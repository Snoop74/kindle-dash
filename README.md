# kindle-dash

Kindle Paperwhite 4 info screen: date, Gebze weather, BTC, USD/EUR (TCMB), daily proverb.

- `generator/render.py` renders `dashboard.png` (1072x1448 grayscale). `--mock` for offline preview.
- `.github/workflows/render.yml` renders at 05:30 and 16:30 (Istanbul) and publishes to GitHub Pages:
  `https://snoop74.github.io/kindle-dash/dashboard.png`
- `kindle/` is the KUAL extension, copy to `/mnt/us/extensions/kindle-dash/` on the Kindle.

## Kindle usage
KUAL → Kindle Dash → "1) Test" (one-shot) or "2) Dashboard'u baslat".
Exit dashboard mode: hold power button ~20 s to restart the Kindle.
Log: `extensions/kindle-dash/dash.log`.
