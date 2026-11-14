"""Score a prompt version on the 40-pair practice set (never the test set). Usage: JEV_PROMPT=v2 python src/dev_eval.py"""
import json
from concurrent.futures import ThreadPoolExecutor
from jev_match import ask_jev, summarize, load_key, ROOT, PROMPT

pairs = json.load(open(ROOT / "data" / "dev40.json"))
gold = json.load(open(ROOT / "data" / "dev40_labels.json"))
key = load_key()
with ThreadPoolExecutor(max_workers=6) as ex:
    res = dict(ex.map(lambda p: (p["pair_id"], summarize(ask_jev(p["pm"], p["k"], key))), pairs))
json.dump(res, open(ROOT / "data" / f"dev40_jev_{PROMPT}.json", "w"), indent=1)
fp = sum(res[k]["decision"] == "same" and gold[k] != "same" for k in gold)
fn = sum(res[k]["decision"] != "same" and gold[k] == "same" for k in gold)
three = sum(res[k]["decision"] == gold[k] for k in gold)
print(f"{PROMPT}: same-vs-not acc {(40-fp-fn)/40:.2f}  false {fp}  missed {fn}/{sum(v=='same' for v in gold.values())}  3-way {three/40:.2f}")
for p in pairs:
    r = res[p["pair_id"]]
    if (r["decision"] == "same") != (gold[p["pair_id"]] == "same"):
        print("  ", gold[p["pair_id"]], "->", r["decision"], round(r["confidence"], 2), "|", p["pm"]["title"], "||", p["k"]["title"])
