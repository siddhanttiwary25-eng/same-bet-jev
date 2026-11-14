"""Find look-alike market pairs across venues (the 'retrieval' step).

For each Polymarket yes/no market, take the closest Kalshi markets by title wording
(rapidfuzz token_set_ratio). Wording-similar pairs are exactly where matching is hard:
many are the same event, many differ by a date, threshold, or candidate.

Writes data/candidates.json: [{pair_id, pm, k, fuzz}]
"""
import json, pathlib, re
from rapidfuzz import process, fuzz

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
NOISE = re.compile(r"(House District|Senate District|Assembly District|House \d|Ward |County )", re.I)


def norm(t):
    return re.sub(r"\s+", " ", t.replace("—", " ")).strip()


def main(top_k=2, min_fuzz=72):
    pm = [p for p in json.load(open(DATA / "polymarket.json")) if p["yes_price"] is not None]
    ks = [k for k in json.load(open(DATA / "kalshi.json"))
          if not k["id"].startswith("KXMVE") and not NOISE.search(k["title"]) and k["title"]]
    # dedupe identical Kalshi titles (keep highest volume)
    best = {}
    for k in ks:
        t = norm(k["title"]).lower()
        if t not in best or k["volume"] > best[t]["volume"]:
            best[t] = k
    ks = list(best.values())
    print("polymarket yes/no:", len(pm), "kalshi (filtered):", len(ks))
    ktitles = [norm(k["title"]) for k in ks]
    out = []
    for p in pm:
        hits = process.extract(norm(p["title"]), ktitles, scorer=fuzz.token_set_ratio,
                               limit=top_k, score_cutoff=min_fuzz)
        for _, score, idx in hits:
            out.append({"pm": p, "k": ks[idx], "fuzz": round(score, 1)})
    for i, c in enumerate(out):
        c["pair_id"] = f"p{i:04d}"
    (DATA / "candidates.json").write_text(json.dumps(out))
    print("candidate pairs:", len(out))


if __name__ == "__main__":
    main()
