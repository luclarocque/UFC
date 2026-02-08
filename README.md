# UFC Main Card Scraper

Scrapes UFC past results from ESPN, extracts main-card fights, and produces:

- `ufc_fights.json` with event + fight details
- `ufc_fights.html` with collapsible event cards for easy viewing

## Quick Start

```powershell
python ufc_fights.py --html
```

This writes `ufc_fights.json` and `ufc_fights.html`, then opens the HTML in your default browser.

## Desktop Shortcut (Windows)

1. Right‑click your Desktop → New → Shortcut.
2. For the location, paste:
   ```
   %SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<path-to-parent-folder>\open_ufc_fights.ps1"
   ```
3. Name it `UFC Fights`.
4. (Optional) Right‑click the shortcut → Properties → Change Icon. Use:
   ```
   %SystemRoot%\System32\shell32.dll
   ```
   Then pick an icon you like.
