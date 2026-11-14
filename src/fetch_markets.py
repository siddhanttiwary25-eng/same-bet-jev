"""Pull open markets from Polymarket (Gamma API) and Kalshi (public trade API).

No keys needed. Writes data/polymarket.json and data/kalshi.json in one common shape:
  {venue, id, title, rules, close, yes_price, volume, url}
"""
import json, time, pathlib, ssl, urllib.request, urllib.parse
import certifi

CTX = ssl.create_default_context(cafile=certifi.where())

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)
UA = {"User-Agent": "jev-market-matcher-demo/0.1"}


def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30, context=CTX) as r:
                return json.load(r)
        except Exception as e:  # rate limits / blips
            time.sleep(2 * (attempt + 1))
            last = e
    raise last


def polymarket(max_markets=2500):
    out, offset = [], 0
    while len(out) < max_markets:
        q = urllib.parse.urlencode({"active": "true", "closed": "false", "limit": 100,
                                    "offset": offset, "order": "volumeNum", "ascending": "false"})
        try:
            page = get(f"https://gamma-api.polymarket.com/markets?{q}")
        except Exception:
            break
        if not page:
            break
        for m in page:
            try:
                prices = json.loads(m.get("outcomePrices") or "[]")
                outcomes = json.loads(m.get("outcomes") or "[]")
            except Exception:
                prices, outcomes = [], []
            yes = None
            if outcomes[:2] == ["Yes", "No"] and prices:
                yes = float(prices[0])
            out.append({
                "venue": "polymarket", "id": m["id"], "title": m.get("question", ""),
                "rules": (m.get("description") or "")[:1500], "close": m.get("endDate"),
                "outcomes": outcomes, "yes_price": yes, "volume": float(m.get("volume") or 0),
                "url": f"https://polymarket.com/market/{m.get('slug')}",
            })
        offset += 100
        time.sleep(0.3)
    return out


def kalshi(max_events=60000):
    out, cursor, n = [], None, 0
    while n < max_events:
        q = {"status": "open", "limit": 200, "with_nested_markets": "true"}
        if cursor:
            q["cursor"] = cursor
        page = get("https://api.elections.kalshi.com/trade-api/v2/events?" + urllib.parse.urlencode(q))
        for ev in page.get("events", []):
            n += 1
            for m in ev.get("markets", []):
                if m.get("status") != "active":
                    continue
                yes = m.get("yes_ask_dollars") or m.get("last_price_dollars")
                title = m.get("title", "")
                sub = m.get("yes_sub_title") or ""
                if sub and sub.lower() not in title.lower():
                    title = f"{title} — {sub}"
                out.append({
                    "venue": "kalshi", "id": m["ticker"], "title": title,
                    "event_title": ev.get("title", ""), "category": ev.get("category", ""),
                    "rules": ((m.get("rules_primary") or "") + " " + (m.get("rules_secondary") or "")).strip()[:1500],
                    "close": m.get("close_time"), "yes_price": float(yes) if yes else None,
                    "volume": float(m.get("volume_fp") or 0),
                    "url": f"https://kalshi.com/markets/{ev.get('series_ticker','').lower()}",
                })
        cursor = page.get("cursor")
        if not cursor:
            break
        time.sleep(0.3)
    return out


if __name__ == "__main__":
    pm = polymarket()
    (DATA / "polymarket.json").write_text(json.dumps(pm))
    print("polymarket markets:", len(pm))
    ks = kalshi()
    (DATA / "kalshi.json").write_text(json.dumps(ks))
    print("kalshi markets:", len(ks))
