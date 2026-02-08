import re
import json
import html
import argparse
import webbrowser
from pathlib import Path
import requests
from bs4 import BeautifulSoup

SCHEDULE_URL = "https://www.espn.com/mma/schedule/_/league/ufc"

EVENT_TITLE_RE = re.compile(r"^UFC \d{3}\b")
WEIGHT_LIMITS = {
    "Strawweight": 115,
    "Flyweight": 125,
    "Bantamweight": 135,
    "Featherweight": 145,
    "Lightweight": 155,
    "Welterweight": 170,
    "Middleweight": 185,
    "Light Heavyweight": 205,
    "Heavyweight": 265,
    "Women's Strawweight": 115,
    "Women's Flyweight": 125,
    "Women's Bantamweight": 135,
    "Women's Featherweight": 145,
}


def format_weightclass(name):
    if not name:
        return name
    limit = WEIGHT_LIMITS.get(name)
    if limit:
        return f"{name} ({limit} lbs)"
    for base in sorted(WEIGHT_LIMITS.keys(), key=len, reverse=True):
        if name.startswith(base + " - "):
            return name.replace(base, f"{base} ({WEIGHT_LIMITS[base]} lbs)", 1)
    return name


def fetch(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text


def parse_event_links(schedule_html):
    soup = BeautifulSoup(schedule_html, "html.parser")
    # Find Past Results table and collect event links matching UFC ZZZ
    past_results = soup.find(string=re.compile(r"Past Results"))
    if not past_results:
        return []
    table = past_results.find_parent(class_="ResponsiveTable")
    if not table:
        table = past_results.find_parent()
    links = []
    for row in table.select("tbody tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        date_text = cells[0] if cells else None
        event_link = None
        event_title = None
        for a in row.find_all("a", href=True):
            title = a.get_text(strip=True)
            if EVENT_TITLE_RE.match(title):
                event_link = "https://www.espn.com" + a["href"]
                event_title = title
                break
        if event_link and event_title:
            links.append((event_link, event_title, date_text))
    return links


def parse_main_card(event_html):
    token = "window['__espnfitt__']="
    start = event_html.find(token)
    if start == -1:
        return []
    start += len(token)
    while start < len(event_html) and event_html[start].isspace():
        start += 1
    if start >= len(event_html) or event_html[start] != "{":
        return []

    # Extract JSON object with brace matching that respects strings.
    depth = 0
    in_str = False
    esc = False
    end = None
    for i in range(start, len(event_html)):
        ch = event_html[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
    if end is None:
        return []

    try:
        data = json.loads(event_html[start:end])
    except json.JSONDecodeError:
        return []

    gamepackage = data.get("page", {}).get("content", {}).get("gamepackage", {})
    card_segs = gamepackage.get("cardSegs", [])
    main_seg = next((s for s in card_segs if s.get("hdr") == "Main Card"), None)
    if not main_seg:
        return []

    fights = []
    for idx, match in enumerate(main_seg.get("mtchs", []), start=1):
        method = match.get("dec", {}).get("shrtDspNm")
        rd = match.get("status", {}).get("rd")
        clk = match.get("status", {}).get("dspClk")
        time = f"{rd}, {clk}" if rd and clk else None
        fights.append(
            {
                "Main card fight number": idx,
                "Weightclass": format_weightclass(match.get("nte")),
                "Red corner fighter": match.get("awy", {}).get("dspNm"),
                "Blue corner fighter": match.get("hme", {}).get("dspNm"),
                "How the fight ended": method,
                "What time the fight ended": time,
            }
        )
    return fights


def render_html(events):
    items = []
    for event in events:
        title = html.escape(event.get("Event") or "")
        date_text = html.escape(event.get("Date") or "")
        summary = f"{title} — {date_text}" if date_text else title
        rows = []
        for fight in event.get("Fights", []):
            rows.append(
                "<tr>"
                f"<td>{fight.get('Main card fight number','')}</td>"
                f"<td>{html.escape(str(fight.get('Weightclass','')))}</td>"
                f"<td>{html.escape(str(fight.get('Red corner fighter','')))}</td>"
                f"<td>{html.escape(str(fight.get('Blue corner fighter','')))}</td>"
                f"<td>{html.escape(str(fight.get('How the fight ended','')))}</td>"
                f"<td>{html.escape(str(fight.get('What time the fight ended','')))}</td>"
                "</tr>"
            )
        table = (
            "<table><thead><tr>"
            "<th>#</th><th>Weightclass</th><th>Red corner</th><th>Blue corner</th>"
            "<th>How ended</th><th>Time</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        )
        items.append(f"<details><summary>{summary}</summary>{table}</details>")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>UFC Main Card Results</title>
  <style>
    :root {{
      --bg: #0c1016;
      --card: #121824;
      --text: #e6eef7;
      --muted: #9fb0c4;
      --border: #1e2a3a;
      --accent: #ffb347;
    }}
    body {{
      margin: 0;
      font-family: "Georgia", "Times New Roman", serif;
      background: radial-gradient(1200px 800px at 20% -10%, #1a2232 0%, var(--bg) 60%);
      color: var(--text);
      padding: 24px;
      display: flex;
      justify-content: center;
    }}
    .container {{
      width: min(900px, 94vw);
    }}
    h1 {{
      margin: 0 0 16px 0;
      font-size: 28px;
      letter-spacing: 0.5px;
    }}
    details {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      margin: 12px 0;
      padding: 10px 14px;
    }}
    summary {{
      cursor: pointer;
      font-weight: 700;
      list-style: none;
      color: var(--accent);
    }}
    summary::-webkit-details-marker {{
      display: none;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-family: "Trebuchet MS", "Verdana", sans-serif;
      font-size: 14px;
    }}
    th, td {{
      padding: 12px 8px;
      border-bottom: 1px solid var(--border);
      text-align: left;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 12px;
      letter-spacing: 0.06em;
    }}
    tr:hover td {{
      background: rgba(255, 255, 255, 0.03);
    }}
    .hint {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 12px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>UFC Main Cards - Spoiler-free</h1>
    {''.join(items)}
  </div>
</body>
</html>
"""


def cache_key(title, date_text):
    return f"{(title or '').strip()}|{(date_text or '').strip()}"


def load_cache(path):
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    cache = {}
    for event in data:
        key = cache_key(event.get("Event"), event.get("Date"))
        if key:
            cache[key] = event
    return cache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--html",
        action="store_true",
        help="Write ufc_fights.json and ufc_fights.html, then open in browser.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore cache and re-fetch all events.",
    )
    args = parser.parse_args()

    schedule_html = fetch(SCHEDULE_URL)
    event_links = parse_event_links(schedule_html)

    out_json = Path.cwd() / "ufc_fights.json"
    cache = {} if args.refresh else load_cache(out_json)

    results = []
    for url, title, date_text in event_links:
        key = cache_key(title, date_text)
        cached = cache.get(key)
        if cached and cached.get("Fights"):
            fights = cached.get("Fights")
        else:
            event_html = fetch(url)
            fights = parse_main_card(event_html)
        results.append(
            {
                "Event": title,
                "Date": date_text,
                "Fights": fights,
            }
        )

    if args.html:
        out_html = Path.cwd() / "ufc_fights.html"
        out_json.write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        out_html.write_text(render_html(results), encoding="utf-8")
        webbrowser.open(out_html.resolve().as_uri(), new=2)
        return

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
