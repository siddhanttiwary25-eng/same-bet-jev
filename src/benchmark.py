"""Run Jev on the 200 hand-labeled pairs and compare with fuzzy title matching.

Fairness rules (no look-ahead for Jev):
  * Jev: we take its top choice as-is. No threshold tuned on this answer key.
  * Fuzzy baseline: we give it its BEST possible cutoff on this same answer key
    (an optimistic upper bound for string matching).
Writes data/jev_results.json and results/benchmark.json.
"""
import json, pathlib, statistics
from concurrent.futures import ThreadPoolExecutor
from jev_match import ask_jev, summarize, load_key, PRICE_PER_MTOK, ROOT, PROMPT

DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)


def prf(pred, gold):
    tp = sum(p and g for p, g in zip(pred, gold)); fp = sum(p and not g for p, g in zip(pred, gold))
    fn = sum(g and not p for p, g in zip(pred, gold)); tn = len(gold) - tp - fp - fn
    prec = tp / (tp + fp) if tp + fp else 0.0; rec = tp / (tp + fn) if tp + fn else 0.0
    return {"accuracy": round((tp + tn) / len(gold), 3), "precision": round(prec, 3), "recall": round(rec, 3),
            "false_matches": fp, "missed_matches": fn, "tp": tp, "tn": tn}


def main():
    pairs = json.load(open(DATA / "sample200.json"))
    labels = json.load(open(DATA / "labels.json"))
    pairs = [p for p in pairs if labels[p["pair_id"]] != "unsure"]
    cache_f = DATA / f"jev_results_{PROMPT}.json"
    cache = json.load(open(cache_f)) if cache_f.exists() else {}
    todo = [p for p in pairs if p["pair_id"] not in cache]
    key = load_key() if todo else None  # saved answers can be re-scored without a key

    def run(p):
        return p["pair_id"], summarize(ask_jev(p["pm"], p["k"], key))
    with ThreadPoolExecutor(max_workers=6) as ex:
        for pid, s in ex.map(run, todo):
            cache[pid] = s
    cache_f.write_text(json.dumps(cache, indent=1))

    gold = [labels[p["pair_id"]] == "same" for p in pairs]
    jev = [cache[p["pair_id"]] for p in pairs]
    jev_pred = [j["decision"] == "same" for j in jev]
    three_way = sum(j["decision"] == labels[p["pair_id"]] for j, p in zip(jev, pairs)) / len(pairs)

    # fuzzy baseline: best cutoff in hindsight
    best = None
    for cut in range(70, 101):
        r = prf([p["fuzz"] >= cut for p in pairs], gold)
        if best is None or r["accuracy"] > best[1]["accuracy"]:
            best = (cut, r)

    # confidence routing: auto-act only on confident 'same'
    hi = [(j, g) for j, g in zip(jev, gold) if j["confidence"] >= 0.8]
    lat = [j["latency_ms"] for j in jev]; toks = [j["input_tokens"] for j in jev]
    out = {
        "n_pairs": len(pairs), "n_true_matches": sum(gold), "model": jev[0]["model"], "prompt": PROMPT,
        "jev": {**prf(jev_pred, gold), "three_way_accuracy": round(three_way, 3)},
        "fuzzy_best_cutoff": {"cutoff": best[0], **best[1]},
        "fuzzy_at_90": prf([p["fuzz"] >= 90 for p in pairs], gold),
        "jev_high_confidence": {"share_of_pairs": round(len(hi) / len(jev), 3),
                                **prf([j["decision"] == "same" for j, _ in hi], [g for _, g in hi])},
        "latency_ms": {"median": statistics.median(lat), "p90": sorted(lat)[int(0.9 * len(lat)) - 1]},
        "tokens_per_pair": round(statistics.mean(toks)),
        "cost_usd_this_run": round(sum(toks) / 1e6 * PRICE_PER_MTOK, 5),
        "cost_usd_per_million_pairs": round(statistics.mean(toks) * PRICE_PER_MTOK, 2),
    }
    # error list for the write-up
    out["jev_errors"] = [{"pair_id": p["pair_id"], "polymarket": p["pm"]["title"], "kalshi": p["k"]["title"],
                          "gold": labels[p["pair_id"]], "jev": j["decision"], "confidence": round(j["confidence"], 2)}
                         for p, j in zip(pairs, jev) if (j["decision"] == "same") != (labels[p["pair_id"]] == "same")]
    (RES / f"benchmark_{PROMPT}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "jev_errors"}, indent=1))
    print("jev errors:", len(out["jev_errors"]))


if __name__ == "__main__":
    main()
