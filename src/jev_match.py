"""Ask Jev whether two prediction markets are the same bet.

One request per pair, four questions (evaluated in parallel by Jev):
  relationship  Choice: same / variant / different   -> the routing decision
  same_subject  Noul:   same person/team/entity/event?
  same_terms    Noul:   same threshold/outcome condition?
  same_window   Noul:   same deadline/time window?
The three Nouls explain *why* a pair isn't a match, which is what a trader or ops person needs.
"""
import json, os, pathlib, ssl, time, urllib.request
import certifi

ROOT = pathlib.Path(__file__).resolve().parent.parent
CTX = ssl.create_default_context(cafile=certifi.where())
MODEL = os.environ.get("JEV_MODEL", "jev-1.14.0")
PRICE_PER_MTOK = 0.042  # USD per million input tokens; output tokens are free (docs.typesafe.ai/models)


def load_key():
    if os.environ.get("TYPESAFE_API_KEY"):
        return os.environ["TYPESAFE_API_KEY"]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("TYPESAFE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("No TYPESAFE_API_KEY: put it in typesafe-jev-demo/.env")


def market_view(m):
    return {
        "venue": m["venue"],
        "question": m["title"],
        "resolution_rules": (m.get("rules") or "")[:900],
        "market_closes": (m.get("close") or "")[:10],
    }


QUESTIONS = {
    "relationship": {
        "type": "choice",
        "instructions": "Market A and Market B are prediction markets on two different exchanges. "
                        "Would a YES share on Market A and a YES share on Market B pay out in exactly the same "
                        "real-world outcomes, so a trader could treat them as the same bet?",
        "criteria": {
            "same": {"means": "Same event, same outcome condition, same deadline: both resolve YES in exactly the same situations.",
                     "ignore": "Wording, punctuation, team nicknames, and a market's administrative close date when the underlying event and deadline are the same."},
            "variant": {"means": "Same underlying event or question family, but they pay out in different situations.",
                        "examples": ["different candidate or team in the same race",
                                     "win the nomination vs run for the nomination",
                                     "different price threshold, seat count, or margin",
                                     "different deadline or year",
                                     "win the election vs win the first round"]},
            "different": "About different events altogether; any wording overlap is coincidental.",
        },
    },
    "same_subject": {"type": "noul",
                     "instructions": "Are both markets about the same specific person, team, company, or entity?"},
    "same_terms": {"type": "noul",
                   "instructions": "Do both markets use the same outcome condition (same achievement, threshold, seat count, margin, or result)?"},
    "same_window": {"type": "noul",
                    "instructions": "Do both markets cover the same time window or deadline for the event (ignore administrative close dates)?"},
}


# v2: tuned on the separate 40-pair practice set (data/dev40.json) only, never on the test set.
# Changes: judge from the resolution rules (titles on Kalshi often drop the season/year),
# say what does NOT make a variant (venue boilerplate, data sources, admin close dates),
# and drop the market close date from the input since venues set it administratively.
QUESTIONS_V2 = {
    "relationship": {
        "type": "choice",
        "instructions": "Market A and Market B are prediction markets on two different exchanges. Read each market's "
                        "resolution rules, not just its title: exchanges word titles differently and often leave out "
                        "the season or year that the rules state. Decide whether a YES share on A and a YES share on B "
                        "pay out in the same real-world outcomes.",
        "criteria": {
            "same": {"means": "Same subject, same outcome condition, same season or deadline. In any realistic scenario both resolve the same way.",
                     "ignore": "Title wording, team nicknames, a missing year in one title when the rules state it, exchange disclaimers, "
                               "which news sources are used, how cancellations or ties are handled, and when trading closes.",
                     "examples": ["'Will Arsenal win the 2026-27 EPL?' vs 'Will Arsenal win the English Premier League?' when the rules name the 2026-27 season",
                                  "'by December 31, 2026' vs 'before Jan 1, 2027'"]},
            "variant": {"means": "Same race, league or question family, but a concrete difference in who, what threshold, which deadline, "
                                 "or what event triggers YES, so they can resolve differently.",
                        "examples": ["different candidate or team in the same race",
                                     "win the nomination vs run for the nomination",
                                     "IPO completed vs S-1 declared effective",
                                     "exactly 4 vs at least 4",
                                     "global chart vs US chart",
                                     "different year or deadline"]},
            "different": "About different events or competitions altogether; any wording overlap is coincidental.",
        },
    },
    **{k: v for k, v in QUESTIONS.items() if k != "relationship"},
}
PROMPT = os.environ.get("JEV_PROMPT", "v1")


def ask_jev(pm, k, key, retries=4):
    qs = QUESTIONS_V2 if PROMPT == "v2" else QUESTIONS
    view = market_view
    if PROMPT == "v2":
        view = lambda m: {kk: vv for kk, vv in market_view(m).items() if kk != "market_closes"}
    body = json.dumps({"model": MODEL,
                       "state": {"market_a": view(pm), "market_b": view(k)},
                       "questions": qs}).encode()
    req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    for attempt in range(retries):
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                out = json.load(r)
            out["latency_ms"] = round((time.perf_counter() - t0) * 1000)
            return out
        except urllib.error.HTTPError as e:
            if e.code in (429, 529) and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Jev HTTP {e.code}: {e.read().decode()[:400]}")


def summarize(resp):
    a = resp["answers"]
    rel = a["relationship"]
    return {
        "decision": rel["choice"],
        "confidence": rel["confidence"],
        "probabilities": rel["probabilities"],
        "same_subject": a["same_subject"]["noul"],
        "same_terms": a["same_terms"]["noul"],
        "same_window": a["same_window"]["noul"],
        "latency_ms": resp["latency_ms"],
        "input_tokens": resp["usage"]["input_tokens"],
        "model": resp["model"],
    }


if __name__ == "__main__":  # smoke test on one pair
    pairs = json.load(open(ROOT / "data" / "sample200.json"))
    p = pairs[0]
    print(p["pm"]["title"], "||", p["k"]["title"])
    print(json.dumps(summarize(ask_jev(p["pm"], p["k"], load_key())), indent=1))
