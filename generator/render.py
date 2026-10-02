"""Render Kindle dashboard PNGs (8-bit grayscale) for common Kindle resolutions.

Data sources (no API keys needed):
  - Weather: Open-Meteo
  - BTC:     CoinGecko
  - FX:      TCMB indicative rates (Döviz Satış)
Run with --mock to render with sample data (offline preview).
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

# ---------- config ----------
W, H = 1080, 1440  # design canvas (3:4); scaled to each Kindle size on save
SIZES = [(600, 800), (758, 1024), (1072, 1448)]
TZ = ZoneInfo("Europe/Istanbul")
CITY_NAME = os.getenv("DASH_CITY", "Gebze")
LAT = float(os.getenv("DASH_LAT", "40.802"))
LON = float(os.getenv("DASH_LON", "29.430"))
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.getenv("DASH_FONT_DIR", "/usr/share/fonts/truetype/dejavu")

DAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
DAYS_SHORT_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
MONTHS_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
             "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# WMO weather code -> (Turkish label, icon key)
WMO = {
    0: ("Açık", "sun"), 1: ("Az bulutlu", "sun_cloud"), 2: ("Parçalı bulutlu", "sun_cloud"),
    3: ("Kapalı", "cloud"), 45: ("Sisli", "fog"), 48: ("Kırağılı sis", "fog"),
    51: ("Hafif çisenti", "rain"), 53: ("Çisenti", "rain"), 55: ("Yoğun çisenti", "rain"),
    61: ("Hafif yağmur", "rain"), 63: ("Yağmurlu", "rain"), 65: ("Kuvvetli yağmur", "rain"),
    66: ("Dondurucu yağmur", "rain"), 67: ("Dondurucu yağmur", "rain"),
    71: ("Hafif kar", "snow"), 73: ("Karlı", "snow"), 75: ("Yoğun kar", "snow"), 77: ("Kar taneli", "snow"),
    80: ("Sağanak", "rain"), 81: ("Sağanak", "rain"), 82: ("Şiddetli sağanak", "rain"),
    85: ("Kar sağanağı", "snow"), 86: ("Kar sağanağı", "snow"),
    95: ("Gök gürültülü", "storm"), 96: ("Dolu, fırtına", "storm"), 99: ("Dolu, fırtına", "storm"),
}

BLACK, DARK, MID, LIGHT, WHITE = 0, 60, 120, 200, 255


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


F = {
    "date_big": font("DejaVuSans-Bold.ttf", 78),
    "date_sub": font("DejaVuSans.ttf", 40),
    "h": font("DejaVuSans-Bold.ttf", 34),
    "temp": font("DejaVuSans-Bold.ttf", 150),
    "body": font("DejaVuSans.ttf", 36),
    "body_b": font("DejaVuSans-Bold.ttf", 36),
    "small": font("DejaVuSans.ttf", 28),
    "price": font("DejaVuSans-Bold.ttf", 54),
    "quote": font("DejaVuSerif-Italic.ttf", 46),
}


# ---------- data ----------
def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "kindle-dash/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def fetch_weather():
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={LAT}&longitude={LON}"
           "&current=temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset,daylight_duration"
           "&timezone=Europe%2FIstanbul&forecast_days=4")
    d = get_json(url)
    days = []
    for i in range(4):
        days.append({
            "date": d["daily"]["time"][i],
            "code": d["daily"]["weather_code"][i],
            "tmax": d["daily"]["temperature_2m_max"][i],
            "tmin": d["daily"]["temperature_2m_min"][i],
            "rain": d["daily"]["precipitation_probability_max"][i],
            "sunrise": d["daily"]["sunrise"][i][-5:],
            "sunset": d["daily"]["sunset"][i][-5:],
            "daylight": d["daily"]["daylight_duration"][i],
        })
    c = d["current"]
    return {"temp": c["temperature_2m"], "code": c["weather_code"],
            "humidity": c["relative_humidity_2m"], "wind": c["wind_speed_10m"], "days": days}


HISTORY_DAYS = 14


def fetch_btc():
    d = get_json("https://api.coingecko.com/api/v3/simple/price"
                 "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true")
    out = {"price": d["bitcoin"]["usd"], "change": d["bitcoin"]["usd_24h_change"]}
    try:  # 14-day history for sparkline (hourly points), optional
        h = get_json("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
                     f"?vs_currency=usd&days={HISTORY_DAYS}")
        out["history"] = [p[1] for p in h["prices"]]
    except Exception as e:
        print(f"[warn] btc history: {e}", file=sys.stderr)
    return out


def _tcmb_rates(url):
    """Parse a TCMB kurlar XML file -> {'USD': ForexSelling, 'EUR': ForexSelling}."""
    import xml.etree.ElementTree as ET
    req = urllib.request.Request(url, headers={"User-Agent": "kindle-dash/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    out = {}
    for cur in root.findall("Currency"):
        code = cur.get("CurrencyCode")
        if code in ("USD", "EUR"):
            out[code] = float(cur.findtext("ForexSelling"))
    return root.get("Tarih"), out


def fetch_fx():
    # TCMB indicative rates (Döviz Satış). today.xml = latest published bulletin.
    last_date, last = _tcmb_rates("https://www.tcmb.gov.tr/kurlar/today.xml")
    ref = dt.datetime.strptime(last_date, "%d.%m.%Y").date()
    series = [last]  # newest first
    for back in range(1, HISTORY_DAYS + 1):
        day = ref - dt.timedelta(days=back)
        if day.weekday() >= 5:  # no bulletin on weekends
            continue
        try:
            _, rates = _tcmb_rates(f"https://www.tcmb.gov.tr/kurlar/{day:%Y%m}/{day:%d%m%Y}.xml")
            series.append(rates)
        except Exception:
            continue  # holiday or missing file
    prev = series[1] if len(series) > 1 else None
    return {k: {"rate": v,
                "change": (v / prev[k] - 1) * 100 if prev else 0.0,
                "history": [r[k] for r in reversed(series) if k in r]}
            for k, v in last.items()}


def mock_data():
    today = dt.date.today()
    days = [{"date": (today + dt.timedelta(days=i)).isoformat(), "code": c, "tmax": mx,
             "tmin": mn, "rain": r, "sunrise": "07:05", "sunset": "18:47",
             "daylight": 42120} for i, (c, mx, mn, r) in
            enumerate([(2, 22, 14, 10), (61, 19, 13, 70), (3, 18, 12, 30), (0, 21, 11, 0)])]
    return {
        "weather": {"temp": 17.4, "code": 2, "humidity": 68, "wind": 12.0, "days": days},
        "btc": {"price": 112345.0, "change": -1.84,
                "history": [108e3 + 4e3 * __import__("math").sin(i / 9) + i * 25 for i in range(336)]},
        "fx": {"USD": {"rate": 41.52, "change": 0.12,
                       "history": [41.1, 41.15, 41.2, 41.22, 41.3, 41.33, 41.4, 41.45, 41.47, 41.52]},
               "EUR": {"rate": 48.71, "change": -0.21,
                       "history": [48.2, 48.5, 48.4, 48.9, 48.95, 48.7, 48.8, 49.0, 48.81, 48.71]}},
    }


def pick_quote(now, forced=None):
    """Same quote all day; a fixed shuffle mixes the categories."""
    import random
    quotes = json.load(open(os.path.join(HERE, "quotes.json"), encoding="utf-8"))
    quotes = [{"text": q} if isinstance(q, str) else q for q in quotes]
    order = list(range(len(quotes)))
    random.Random(42).shuffle(order)
    if forced is not None:
        return quotes[int(forced) % len(quotes)]
    day = now.date().toordinal()
    return quotes[order[day % len(order)]]


def safe(fn):
    try:
        return fn()
    except Exception as e:  # keep rendering even if one source fails
        print(f"[warn] {fn.__name__}: {e}", file=sys.stderr)
        return None


# ---------- drawing helpers ----------
def text_w(d, s, f):
    return d.textlength(s, font=f)


def draw_icon(d, kind, cx, cy, r):
    """Simple vector weather icons, e-ink friendly."""
    lw = max(4, r // 10)

    def sun(x, y, rr):
        d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=BLACK, width=lw)
        import math
        for i in range(8):
            a = i * math.pi / 4
            d.line([x + math.cos(a) * rr * 1.35, y + math.sin(a) * rr * 1.35,
                    x + math.cos(a) * rr * 1.75, y + math.sin(a) * rr * 1.75], fill=BLACK, width=lw)

    def cloud(x, y, rr, fill=WHITE):
        parts = [(x - rr * 0.55, y + rr * 0.1, rr * 0.5), (x, y - rr * 0.2, rr * 0.65),
                 (x + rr * 0.6, y + rr * 0.15, rr * 0.45)]
        for px, py, pr in parts:
            d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=fill, outline=BLACK, width=lw)
        d.rectangle([x - rr * 0.55, y + rr * 0.1, x + rr * 0.6, y + rr * 0.6], fill=fill)
        d.line([x - rr * 0.55, y + rr * 0.6, x + rr * 0.6, y + rr * 0.6], fill=BLACK, width=lw)
        for px, py, pr in parts:  # redraw inner outline cleanup
            pass

    if kind == "sun":
        sun(cx, cy, r * 0.55)
    elif kind == "sun_cloud":
        sun(cx - r * 0.3, cy - r * 0.3, r * 0.4)
        cloud(cx + r * 0.1, cy + r * 0.15, r * 0.75)
    elif kind == "cloud":
        cloud(cx, cy, r * 0.85, fill=LIGHT)
    elif kind == "fog":
        for i in range(4):
            y = cy - r * 0.45 + i * r * 0.3
            d.line([cx - r * 0.8, y, cx + r * 0.8, y], fill=BLACK, width=lw)
    elif kind in ("rain", "snow", "storm"):
        cloud(cx, cy - r * 0.25, r * 0.75, fill=LIGHT)
        for i in range(3):
            x = cx - r * 0.45 + i * r * 0.45
            y = cy + r * 0.5
            if kind == "rain":
                d.line([x, y, x - r * 0.12, y + r * 0.35], fill=BLACK, width=lw)
            elif kind == "snow":
                d.ellipse([x - lw * 1.3, y + r * 0.1, x + lw * 1.3, y + r * 0.1 + lw * 2.6], fill=BLACK)
            else:
                if i == 1:
                    d.polygon([(x, y), (x - r * 0.2, y + r * 0.25), (x, y + r * 0.25),
                               (x - r * 0.15, y + r * 0.55), (x + r * 0.2, y + r * 0.15),
                               (x, y + r * 0.15), (x + r * 0.12, y)], fill=BLACK)


def draw_sparkline(d, values, box):
    """Min-max scaled line chart with a light fill and an end dot."""
    if not values or len(values) < 2:
        return
    x0, y0, x1, y1 = box
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    n = len(values)
    pts = [(x0 + (x1 - x0) * i / (n - 1), y1 - (y1 - y0) * (v - lo) / span)
           for i, v in enumerate(values)]
    d.polygon(pts + [(x1, y1), (x0, y1)], fill=235)
    d.line([x0, y1, x1, y1], fill=LIGHT, width=2)
    d.line(pts, fill=BLACK, width=4, joint="curve")
    ex, ey = pts[-1]
    d.ellipse([ex - 7, ey - 7, ex + 7, ey + 7], fill=BLACK)


def wrap(d, s, f, max_w):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_w(d, t, f) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fmt_num(v, decimals=2):
    s = f"{v:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")  # Turkish format


def change_str(ch):
    arrow = "▲" if ch >= 0 else "▼"
    return f"{arrow} %{fmt_num(abs(ch))}"


# ---------- render ----------
def draw_modern(data, now):
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    M = 64  # side margin
    y = 56

    # Header: date
    d.text((M, y), f"{now.day} {MONTHS_TR[now.month - 1]}", font=F["date_big"], fill=BLACK)
    y += 92
    d.text((M, y), f"{DAYS_TR[now.weekday()]}, {now.year}", font=F["date_sub"], fill=DARK)
    upd = f"Güncellendi {now:%H:%M}"
    d.text((W - M - text_w(d, upd, F["small"]), y + 10), upd, font=F["small"], fill=MID)
    y += 76
    d.line([M, y, W - M, y], fill=BLACK, width=4)
    y += 36

    # Weather
    wx = data.get("weather")
    city = CITY_NAME.replace("i", "İ").replace("ı", "I").upper()  # Turkish casing
    d.text((M, y), city, font=F["h"], fill=DARK)
    y += 54
    if wx:
        label, icon = WMO.get(wx["code"], ("—", "cloud"))
        draw_icon(d, icon, M + 110, y + 95, 110)
        t = f"{round(wx['temp'])}°"
        d.text((M + 250, y - 10), t, font=F["temp"], fill=BLACK)
        rx = M + 250 + text_w(d, t, F["temp"]) + 30
        today = wx["days"][0]
        d.text((rx, y + 22), label, font=F["body_b"], fill=BLACK)
        d.text((rx, y + 72), f"{round(today['tmin'])}° / {round(today['tmax'])}°", font=F["body"], fill=DARK)
        d.text((rx, y + 118), f"Yağış %{today['rain']}  ·  Nem %{wx['humidity']}", font=F["small"], fill=DARK)
        y += 230

        # next 3 days
        col_w = (W - 2 * M) / 3
        for i, day in enumerate(wx["days"][1:4]):
            cx = M + col_w * i + col_w / 2
            dd = dt.date.fromisoformat(day["date"])
            name = DAYS_SHORT_TR[dd.weekday()]
            d.text((cx - text_w(d, name, F["body_b"]) / 2, y), name, font=F["body_b"], fill=BLACK)
            draw_icon(d, WMO.get(day["code"], ("", "cloud"))[1], cx, y + 105, 55)
            tt = f"{round(day['tmin'])}° / {round(day['tmax'])}°"
            d.text((cx - text_w(d, tt, F["body"]) / 2, y + 170), tt, font=F["body"], fill=DARK)
            rr = f"☂ %{day['rain']}"
            d.text((cx - text_w(d, rr, F["small"]) / 2, y + 218), rr, font=F["small"], fill=MID)
        y += 280
    else:
        d.text((M, y), "Hava durumu alınamadı", font=F["body"], fill=MID)
        y += 80

    d.line([M, y, W - M, y], fill=LIGHT, width=3)
    y += 36

    # Markets
    d.text((M, y), "PİYASA", font=F["h"], fill=DARK)
    y += 60
    rows = []
    if data.get("btc"):
        b = data["btc"]
        rows.append(("BTC", f"${fmt_num(b['price'], 0)}", b["change"], b.get("history")))
    fx = data.get("fx") or {}
    for k in ("USD", "EUR"):
        if k in fx:
            rows.append((f"{k}/TRY", f"₺{fmt_num(fx[k]['rate'])}", fx[k]["change"],
                         fx[k].get("history")))
    if not rows:
        d.text((M, y), "Piyasa verisi alınamadı", font=F["body"], fill=MID)
        y += 70
    spark_x0 = M + 230 + max((text_w(d, r[1], F["price"]) for r in rows), default=0) + 40
    spark_x1 = W - M - max((text_w(d, change_str(r[2]), F["body"]) for r in rows), default=0) - 40
    for name, price, ch, hist in rows:
        d.text((M, y + 12), name, font=F["body_b"], fill=DARK)
        d.text((M + 230, y), price, font=F["price"], fill=BLACK)
        if hist and spark_x1 - spark_x0 > 80:
            draw_sparkline(d, hist, (spark_x0, y + 10, spark_x1, y + 62))
        cs = change_str(ch)
        d.text((W - M - text_w(d, cs, F["body"]), y + 12), cs, font=F["body"], fill=DARK)
        y += 84
    if any(r[3] for r in rows):
        lbl = f"Grafikler: son {HISTORY_DAYS} gün"
        d.text((W - M - text_w(d, lbl, F["small"]), y - 4), lbl, font=F["small"], fill=MID)
        y += 30
    y += 10
    d.line([M, y, W - M, y], fill=LIGHT, width=3)

    # Quote of the day (fills remaining space, vertically centered)
    q = pick_quote(now, os.getenv("DASH_QUOTE_INDEX"))
    text, author = q["text"], q.get("author")
    area_top, area_bot = y + 24, H - 50
    max_w = W - 2 * M - 40
    # Shrink font until the quote fits the remaining area
    for size in (46, 42, 38, 34, 30):
        qf = font("DejaVuSerif-Italic.ttf", size)
        af = font("DejaVuSans.ttf", int(size * 0.74))
        lines = wrap(d, f"“{text}”", qf, max_w)
        lh = int(size * 1.38)
        block = len(lines) * lh + (int(size * 1.2) if author else 0)
        if block <= area_bot - area_top:
            break
    qy = area_top + (area_bot - area_top - block) / 2
    for ln in lines:
        d.text(((W - text_w(d, ln, qf)) / 2, qy), ln, font=qf, fill=BLACK)
        qy += lh
    if author:
        a = f"— {author}"
        d.text(((W - text_w(d, a, af)) / 2, qy + size * 0.35), a, font=af, fill=MID)

    return img


def render(data, out_path):
    now = dt.datetime.now(TZ)
    if os.getenv("DASH_NOW"):  # testing: DASH_NOW=2026-10-15T06:00
        now = dt.datetime.fromisoformat(os.getenv("DASH_NOW")).replace(tzinfo=TZ)
    theme = os.getenv("DASH_THEME", "takvim")
    if theme == "takvim":
        from takvim import draw_takvim
        img = draw_takvim(data, now)
    else:
        img = draw_modern(data, now)
    # Default file + one per known Kindle resolution (dashboard_600x800.png ...)
    base = out_path[:-4] if out_path.endswith(".png") else out_path
    img.save(out_path, optimize=True)
    print(f"saved {out_path}")
    for sw, sh in SIZES:
        p = f"{base}_{sw}x{sh}.png"
        img.resize((sw, sh), Image.LANCZOS).save(p, optimize=True)
        print(f"saved {p}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--out", default="dashboard.png")
    a = ap.parse_args()
    if a.mock:
        data = mock_data()
    else:
        data = {"weather": safe(fetch_weather), "btc": safe(fetch_btc), "fx": safe(fetch_fx)}
    render(data, a.out)


if __name__ == "__main__":
    main()
