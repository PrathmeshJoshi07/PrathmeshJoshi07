export GITHUB_TOKEN=ghp_yourTokenHere
export TARGET_USERNAME=PrathmeshJoshi07
python tools/generate_streak_svg.py
# tools/generate_streak_svg.py
# Usage: run in repository root. Requires env var GITHUB_TOKEN and optional TARGET_USERNAME.
import os, sys, requests, datetime
from textwrap import dedent

GITHUB_API = "https://api.github.com/graphql"

def get_username():
    env_user = os.getenv("TARGET_USERNAME")
    if env_user:
        return env_user
    repo = os.getenv("GITHUB_REPOSITORY")
    if repo and "/" in repo:
        return repo.split("/")[0]
    print("ERROR: set TARGET_USERNAME env var or run in GitHub Action with GITHUB_REPOSITORY set.")
    sys.exit(1)

def run_graphql(query, variables=None, token=None):
    headers = {"Authorization": f"bearer {token}", "Accept":"application/json"}
    r = requests.post(GITHUB_API, json={"query": query, "variables": variables or {}}, headers=headers, timeout=30)
    if r.status_code != 200:
        raise Exception(f"GraphQL query failed: {r.status_code} {r.text}")
    payload = r.json()
    if "errors" in payload:
        raise Exception(f"GraphQL errors: {payload['errors']}")
    return payload["data"]

def fetch_contribution_calendar(username, token):
    today = datetime.date.today()
    one_year_ago = today - datetime.timedelta(days=365)
    query = """
    query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    variables = {
        "login": username,
        "from": one_year_ago.isoformat()+"T00:00:00Z",
        "to": today.isoformat()+"T23:59:59Z"
    }
    data = run_graphql(query, variables, token)
    cal = data["user"]["contributionsCollection"]["contributionCalendar"]
    return cal

def flatten_days(weeks):
    days = []
    for w in weeks:
        for d in w["contributionDays"]:
            days.append({"date": d["date"], "count": d["contributionCount"]})
    days.sort(key=lambda x: x["date"])
    return days

def compute_streaks(days):
    total = sum(d["count"] for d in days)
    date_to_count = {d["date"]: d["count"] for d in days}
    last_day = datetime.date.fromisoformat(days[-1]["date"])
    cur = 0
    d = last_day
    while True:
        key = d.isoformat()
        cnt = date_to_count.get(key, 0)
        if cnt > 0:
            cur += 1
        else:
            break
        d = d - datetime.timedelta(days=1)
        if d.isoformat() not in date_to_count:
            break
    longest = 0
    running = 0
    for dct in days:
        if dct["count"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0
    return {"total": total, "current": cur, "longest": longest, "lastDate": last_day.isoformat()}

def generate_svg(values, username):
    total = values["total"]
    current = values["current"]
    longest = values["longest"]
    lastDate = values["lastDate"]
    now = datetime.date.today().strftime("%b %d, %Y")
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="900" height="220" viewBox="0 0 900 220" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
  <defs>
    <filter id="glow">
      <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
      <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect width="100%" height="100%" fill="#071018" rx="10"/>
  <g transform="translate(24,18)">
    <text x="0" y="26" font-family="Inter, Roboto, Arial" font-size="20" fill="#00E5FF" font-weight="700">GitHub Streak Stats</text>
    <line x1="0" y1="36" x2="820" y2="36" stroke="#0B2430" stroke-width="1"/>
  </g>
  <g transform="translate(24,56)">
    <rect x="0" y="0" width="260" height="100" rx="8" fill="#06101a" stroke="#0b2830" />
    <text x="24" y="30" font-family="Inter, Roboto, Arial" font-size="12" fill="#9fdbe9">CURRENT STREAK</text>
    <text x="24" y="72" font-family="Inter, Roboto, Arial" font-size="40" fill="#FFD24A" font-weight="700">{current}</text>
    <rect x="320" y="0" width="260" height="100" rx="8" fill="#06101a" stroke="#37220e" />
    <text x="344" y="30" font-family="Inter, Roboto, Arial" font-size="12" fill="#9fdbe9">LONGEST STREAK</text>
    <text x="344" y="72" font-family="Inter, Roboto, Arial" font-size="40" fill="#FFD24A" font-weight="700">{longest}</text>
    <rect x="640" y="0" width="160" height="100" rx="8" fill="#06101a" stroke="#263033" />
    <text x="664" y="30" font-family="Inter, Roboto, Arial" font-size="12" fill="#9fdbe9">TOTAL CONTRIBUTIONS</text>
    <text x="664" y="72" font-family="Inter, Roboto, Arial" font-size="40" fill="#FFD24A" font-weight="700">{total}</text>
  </g>
  <g transform="translate(24,180)">
    <text x="0" y="18" font-family="Inter, Roboto, Arial" font-size="14" fill="#00E5FF">Streak</text>
    <text x="72" y="18" font-family="Inter, Roboto, Arial" font-size="14" fill="#FFD24A">{values.get('current',0)} days</text>
    <text x="300" y="18" font-family="Inter, Roboto, Arial" font-size="12" fill="#9fcfe0">Updated: {now}</text>
    <text x="520" y="18" font-family="Inter, Roboto, Arial" font-size="12" fill="#9fcfe0">User: {username}</text>
    <text x="720" y="18" font-family="Inter, Roboto, Arial" font-size="12" fill="#9fcfe0">Last data: {lastDate}</text>
  </g>
  <rect x="6" y="6" width="888" height="208" rx="12" fill="none" stroke="#00E5FF" stroke-opacity="0.06" />
</svg>
'''
    return svg

def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not found in environment.")
        sys.exit(1)
    username = get_username()
    print(f"Fetching data for {username} ...")
    cal = fetch_contribution_calendar(username, token)
    weeks = cal["weeks"]
    days = flatten_days(weeks)
    stats = compute_streaks(days)
    print("Stats:", stats)
    svg = generate_svg(stats, username)
    out_dir = "assets"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "streak.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
