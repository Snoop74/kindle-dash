"""Nostalgic tear-off calendar leaf ("takvim yaprağı") theme."""
import datetime as dt

from PIL import Image, ImageDraw

import render as R



def tr_upper(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


def centered(d, cx, y, s, f, fill=0):
    d.text((cx - d.textlength(s, font=f) / 2, y), s, font=f, fill=fill)


def spaced(d, cx, y, s, f, max_w, fill=0):
    """Draw letter-spaced caps centered, shrinking spacing to fit."""
    widths = [d.textlength(ch, font=f) for ch in s]
    gap = min(48, (max_w - sum(widths)) / max(1, len(s) - 1))
    total = sum(widths) + gap * (len(s) - 1)
    x = cx - total / 2
    for ch, w in zip(s, widths):
        d.text((x, y), ch, font=f, fill=fill)
        x += w + gap


def draw_takvim(data, now):
    W, H = R.W, R.H
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    cx = W // 2
    today = now.date()
    f = R.font

    # Paper: perforation + double frame
    for x in range(30, W - 20, 26):
        d.ellipse([x, 14, x + 8, 22], fill=170)
    L, T, Rr, B = 34, 40, W - 34, H - 30
    d.rectangle([L, T, Rr, B], outline=0, width=6)
    d.rectangle([L + 14, T + 14, Rr - 14, B - 14], outline=0, width=2)
    il, ir = L + 14, Rr - 14  # inner frame x

    # Info row
    wx = data.get("weather")
    day0 = wx["days"][0] if wx else None
    week = today.isocalendar()[1]
    info = f"{today.year}    ·    {week}. hafta    ·    Yılın {today.timetuple().tm_yday}. günü"
    centered(d, cx, 74, info, f("DejaVuSans.ttf", 32))
    d.line([il, 128, ir, 128], fill=0, width=3)

    # Month, spaced
    spaced(d, cx, 146, tr_upper(R.MONTHS_TR[today.month - 1]), f("DejaVuSans-Bold.ttf", 112), 620)

    # Giant condensed day number, stretched vertically like old leaves
    numf = f("DejaVuSansCondensed-Bold.ttf", 400)
    num = str(today.day)
    tmp = Image.new("L", (int(d.textlength(num, font=numf)) + 20, 480), 255)
    ImageDraw.Draw(tmp).text((10, 0), num, font=numf, fill=0)
    bbox = Image.eval(tmp, lambda p: 255 - p).getbbox()
    tmp = tmp.crop(bbox)
    tw = min(470, tmp.width)
    tmp = tmp.resize((tw, 600), Image.LANCZOS)
    ny = 290
    img.paste(tmp, (cx - tw // 2, ny))

    # Side columns
    lab, val = f("DejaVuSans.ttf", 30), f("DejaVuSans-Bold.ttf", 40)
    ny_side = ny + 40
    lx, rx = il + 125, ir - 125
    if day0:
        centered(d, lx, ny_side + 10, "Güneş", f("DejaVuSans-Bold.ttf", 34))
        R.draw_icon(d, "sun", lx, ny_side + 120, 66)
        centered(d, lx, ny_side + 200, "Doğuş", lab)
        centered(d, lx, ny_side + 240, day0["sunrise"], val)
        centered(d, lx, ny_side + 310, "Batış", lab)
        centered(d, lx, ny_side + 350, day0["sunset"], val)
    if wx:
        label, icon = R.WMO.get(wx["code"], ("—", "cloud"))
        centered(d, rx, ny_side + 10, R.CITY_NAME, f("DejaVuSans-Bold.ttf", 34))
        R.draw_icon(d, icon, rx, ny_side + 122, 66)
        centered(d, rx, ny_side + 200, f"{round(wx['temp'])}°", f("DejaVuSans-Bold.ttf", 56))
        centered(d, rx, ny_side + 275, f"{round(day0['tmin'])}° / {round(day0['tmax'])}°", lab)
        centered(d, rx, ny_side + 320, f"Yağış %{day0['rain']}", lab)
        # wrap long condition label onto two lines if needed
        words = label.split()
        lines = [label] if d.textlength(label, font=lab) < 220 else [" ".join(words[:-1]), words[-1]]
        for i, ln in enumerate(lines):
            centered(d, rx, ny_side + 365 + i * 36, ln, lab)

    # Day / night length
    yb = ny + 620
    if day0 and day0.get("daylight"):
        dl = round(day0["daylight"] / 60)
        nl = 24 * 60 - dl
        centered(d, cx, yb, f"Gündüz: {dl // 60} s. {dl % 60} d.  —  Gece: {nl // 60} s. {nl % 60} d.",
                 f("DejaVuSans.ttf", 28))
    # Day name
    spaced(d, cx, yb + 50, tr_upper(R.DAYS_TR[today.weekday()]), f("DejaVuSans-Bold.ttf", 96), 860)
    y = yb + 170
    d.line([il, y, ir, y], fill=0, width=3)

    # Market strip
    parts = []
    if data.get("btc"):
        parts.append(f"BTC ${R.fmt_num(data['btc']['price'], 0)} {R.change_str(data['btc']['change'])}")
    fx = data.get("fx") or {}
    for k in ("USD", "EUR"):
        if k in fx:
            parts.append(f"{k} ₺{R.fmt_num(fx[k]['rate'])} {R.change_str(fx[k]['change'])}")
    if parts:
        s = "   ·   ".join(parts)
        for size in (30, 28, 26, 24, 22):
            mf = f("DejaVuSans.ttf", size)
            if d.textlength(s, font=mf) <= ir - il - 40:
                break
        centered(d, cx, y + 14, s, mf)
        y += 60
        d.line([il, y, ir, y], fill=0, width=2)

    # Saying of the day
    q = R.pick_quote(now, R.os.getenv("DASH_QUOTE_INDEX"))
    text, author = q["text"], q.get("author")
    top, bot = y + 14, B - 30
    for size in (40, 36, 33, 30, 27):
        qf = f("DejaVuSerif-Bold.ttf", size)
        af = f("DejaVuSans.ttf", int(size * 0.72))
        lines = R.wrap(d, text, qf, ir - il - 80)
        lh = int(size * 1.3)
        block = len(lines) * lh + (int(size * 1.15) if author else 0)
        if block <= bot - top:
            break
    qy = top + (bot - top - block) / 2
    for ln in lines:
        centered(d, cx, qy, ln, qf)
        qy += lh
    if author:
        centered(d, cx, qy + size * 0.25, f"— {author}", af, fill=90)
    return img
