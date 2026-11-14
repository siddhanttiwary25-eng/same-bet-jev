# Same bet? Cross-venue market matching with Jev

Decides whether a Polymarket market and a Kalshi market are the **same bet**, a **variant** (same race, different terms), or **different**, using TypeSafe's Jev. It also benchmarks Jev against title matching on 197 hand-labeled look-alike pairs.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install certifi rapidfuzz
echo "TYPESAFE_API_KEY=sk-..." > .env
.venv/bin/python src/fetch_markets.py   # pull live markets (no keys needed)
.venv/bin/python src/candidates.py      # find look-alike pairs by title
.venv/bin/python src/benchmark.py                   # Jev, first-draft instructions
JEV_PROMPT=v2 .venv/bin/python src/dev_eval.py      # tune on the 40-pair practice set only
JEV_PROMPT=v2 .venv/bin/python src/benchmark.py     # tuned instructions, test set run once (< $0.01)
.venv/bin/python src/build_page.py      # write site/index.html
```

## Files

| File | What it does |
|---|---|
| `src/fetch_markets.py` | Pulls open markets from Polymarket's Gamma API and Kalshi's public API into one shape |
| `src/candidates.py` | For each Polymarket market, keeps the 2 Kalshi markets with the most similar titles |
| `data/sample200.json`, `data/labels.json` | 200 sampled pairs and the answer key (same / variant / different / unsure) |
| `src/jev_match.py` | One Jev request per pair: a same/variant/different choice plus three yes/no checks (subject, terms, deadline) |
| `src/dev_eval.py`, `data/dev40*.json` | Separate 40-pair practice set used to tune the instructions; no markets shared with the test set |
| `data/label_adjudication.json` | The 10 labels corrected after reading full rules, with reasons (originals in `labels_original.json`) |
| `src/benchmark.py` | Scores Jev against the key and against title matching at its best possible cutoff |
| `src/build_page.py`, `src/brief.py` | Results page and GTM brief |

## Results (Nov 13, 2026 snapshot, 197 pairs, 37 true twins)

| Method | Accuracy | False matches | Missed |
|---|---|---|---|
| Jev, tuned instructions | 98% | 0 | 3 |
| Jev, first-draft instructions | 85% | 0 | 30 |
| Title match, best cutoff in hindsight | 83% | 11 | 22 |

About 1,100 input tokens and 0.2s per pair; ~$46 per million pairs.

## Fairness

- Jev's top choice is used as-is, with no threshold tuned on the answer key.
- Title matching gets its best cutoff picked after seeing the answers, so its row is an upper bound.
- Labels were made with AI help and reviewed by hand. 10 were corrected after reading full rules (see `label_adjudication.json`); scores on the original labels are on the results page.
- Instructions were tuned only on the practice set; the test set was run once with the locked version.
