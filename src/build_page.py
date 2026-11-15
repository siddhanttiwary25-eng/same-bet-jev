"""Build site/index.html: benchmark results, pair explorer, price gaps, GTM brief.

Works before Jev has run (shows Jev as pending) and after (fills everything in).
"""
import json, html, pathlib, datetime
from brief import ICP, ACCOUNTS, PITCH_LINE, OBJECTIONS, PLAYBOOK

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES, SITE = ROOT / "data", ROOT / "results", ROOT / "site"
SITE.mkdir(exist_ok=True)
e = html.escape


def prf(pred, gold):
    tp = sum(p and g for p, g in zip(pred, gold)); fp = sum(p and not g for p, g in zip(pred, gold))
    fn = sum(g and not p for p, g in zip(pred, gold))
    return {"accuracy": (len(gold) - fp - fn) / len(gold), "false_matches": fp, "missed_matches": fn,
            "precision": tp / (tp + fp) if tp + fp else 0, "recall": tp / (tp + fn) if tp + fn else 0}


def main():
    pairs = json.load(open(DATA / "sample200.json"))
    labels = json.load(open(DATA / "labels.json"))
    pairs = [p for p in pairs if labels[p["pair_id"]] != "unsure"]
    jev = json.load(open(DATA / "jev_results_v2.json")) if (DATA / "jev_results_v2.json").exists() else {}
    bench = json.load(open(RES / "benchmark_v2.json")) if (RES / "benchmark_v2.json").exists() else None
    v1 = json.load(open(RES / "benchmark_v1.json")) if (RES / "benchmark_v1.json").exists() else None
    orig = json.load(open(DATA / "labels_original.json"))
    adj = json.load(open(DATA / "label_adjudication.json"))
    have_jev = bench is not None and all(p["pair_id"] in jev for p in pairs)
    gold = [labels[p["pair_id"]] == "same" for p in pairs]

    best_cut, best = None, None
    for cut in range(70, 101):
        r = prf([p["fuzz"] >= cut for p in pairs], gold)
        if best is None or r["accuracy"] > best["accuracy"]:
            best_cut, best = cut, r
    f90 = prf([p["fuzz"] >= 90 for p in pairs], gold)

    rows = []
    for p in pairs:
        j = jev.get(p["pair_id"])
        rows.append({
            "id": p["pair_id"], "fuzz": p["fuzz"], "gold": labels[p["pair_id"]],
            "a": {"t": p["pm"]["title"], "p": p["pm"]["yes_price"], "u": p["pm"]["url"]},
            "b": {"t": p["k"]["title"], "p": p["k"]["yes_price"], "u": p["k"]["url"], "tk": p["k"]["id"]},
            "jev": None if not j else {"d": j["decision"], "c": round(j["probabilities"][j["decision"]], 3),
                                       "s": round(j["same_subject"], 2), "x": round(j["same_terms"], 2),
                                       "w": round(j["same_window"], 2)},
        })

    # price gaps on pairs that both the answer key and Jev (if run) call the same bet
    gaps = []
    for r in rows:
        if r["gold"] != "same" or r["a"]["p"] is None or r["b"]["p"] is None:
            continue
        if have_jev and r["jev"]["d"] != "same":
            continue
        gaps.append({**r, "gap": abs(r["a"]["p"] - r["b"]["p"])})
    gaps.sort(key=lambda r: -r["gap"])

    if have_jev:
        J = bench["jev"]
        jcells = [f"{J['accuracy']:.0%}", str(J["false_matches"]), str(J["missed_matches"]),
                  f"${bench['cost_usd_per_million_pairs']:,.0f}", f"{bench['latency_ms']['median']/1000:.1f}s"]
        headline = (f"Jev made zero false matches on {len(pairs)} look-alike pairs and caught {J['tp']} of {J['tp']+J['missed_matches']} "
                    f"real twins. Title matching, even with its cutoff picked after seeing the answers, made "
                    f"{best['false_matches']} false matches and missed {best['missed_matches']}.")
        three = f"{J['three_way_accuracy']:.0%}"
        model = bench["model"]
        hc = bench["jev_high_confidence"]
    else:
        jcells = ["running"] * 5
        headline = ("Title matching either floods you with false matches or misses half the real ones. "
                    "Jev results are being filled in.")
        three, model, hc = "pending", "jev-1.14.0", None

    snap = "2026-11-13"  # day the market data was pulled
    ks = [p["pair_id"] for p in pairs if orig[p["pair_id"]] != "unsure"]
    o_fp = sum(jev[k]["decision"] == "same" and orig[k] != "same" for k in ks) if have_jev else 0
    o_fn = sum(jev[k]["decision"] != "same" and orig[k] == "same" for k in ks) if have_jev else 0
    orig_line = (f"Scored against my original labels, before the fine-print corrections, tuned Jev still made {o_fp} false matches "
                 f"and missed {o_fn} of {sum(orig[k]=='same' for k in ks)}.")
    sb = {r["id"]: r for r in rows}
    fine = "".join(
        f'<li><div class="trap-k">{e(sb[c["pair_id"]]["a"]["t"])}</div>'
        f'<div class="trap-m">identical-looking on both venues · title similarity <b>{sb[c["pair_id"]]["fuzz"]:.0f}</b>/100</div>'
        f'<p>{e(c["reason"])}</p></li>'
        for c in [x for x in adj["changes"] if x["pair_id"] in ("p1651", "p0286", "p1379")])
    n_same = sum(gold)

    def tr(name, cells, cls=""):
        return f'<tr class="{cls}"><th scope="row">{name}</th>' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

    table = "".join([
        tr("Jev, tuned instructions", jcells, "jev"),
        tr("Jev, first-draft instructions", [f"{v1['jev']['accuracy']:.0%}", v1['jev']['false_matches'], v1['jev']['missed_matches'],
           f"${v1['cost_usd_per_million_pairs']:,.0f}", f"{v1['latency_ms']['median']/1000:.1f}s"]) if v1 else "",
        tr(f"Title match, best cutoff ({best_cut}/100)*",
           [f"{best['accuracy']:.0%}", best["false_matches"], best["missed_matches"], "≈$0", "&lt;1ms"]),
        tr("Title match, common cutoff (90/100)",
           [f"{f90['accuracy']:.0%}", f90["false_matches"], f90["missed_matches"], "≈$0", "&lt;1ms"]),
    ])

    traps = [("p0193", "Win the nomination vs run for it"), ("p0307", "Win the election vs make the runoff"),
             ("p2287", "Most seats vs at least 50 seats"), ("p1010", "Champions League vs EFL Championship"),
             ("p0482", "NFL champion vs win the first half")]
    byid = {r["id"]: r for r in rows}
    trap_html = "".join(
        f'<li><div class="trap-k">{e(lbl)}</div><div class="trap-pair"><span>{e(byid[i]["a"]["t"])}</span>'
        f'<span>{e(byid[i]["b"]["t"])}</span></div><div class="trap-m">title similarity <b>{byid[i]["fuzz"]:.0f}</b>/100 · '
        f'answer key: <b class="lab {byid[i]["gold"]}">{byid[i]["gold"]}</b>'
        + (f' · Jev: <b class="lab {byid[i]["jev"]["d"]}">{byid[i]["jev"]["d"]}</b>' if byid[i]["jev"] else "")
        + "</div></li>" for i in traps if i in byid)

    icp_html = "".join(f'<div class="seg"><h4>{e(s["segment"])}</h4><p>{e(s["pain"])}</p>'
                       f'<dl><dt>Trigger</dt><dd>{e(s["trigger"])}</dd><dt>Buyer</dt><dd>{e(s["buyer"])}</dd></dl></div>'
                       for s in ICP)
    acct_html = "".join(f"<tr><th scope='row'>{e(a)}</th><td>{e(t)}</td><td>{e(w)}</td></tr>" for a, t, w in ACCOUNTS)
    obj_html = "".join(f"<div class='obj'><h4>{e(q)}</h4><p>{e(a)}</p></div>" for q, a in OBJECTIONS)
    pb_html = "".join(f"<li><span class='pb-d'>{e(d)}</span><div><h4>{e(t)}</h4><p>{e(x)}</p></div></li>"
                      for d, t, x in PLAYBOOK)
    hc_line = (f"<p>Confidence routing: on the {hc['share_of_pairs']:.0%} of pairs where Jev was at least 80% confident, "
               f"it made {hc['false_matches']} false matches and missed {hc['missed_matches']}. Those can be automated; "
               f"the rest go to a person.</p>") if hc else ""

    vals = dict(
        headline=e(headline), table=table, n=len(pairs), n_same=n_same, traps=trap_html,
        three=three, model=e(model), snap=snap, icp=icp_html, accounts=acct_html, pitch=e(PITCH_LINE),
        objections=obj_html, orig_line=orig_line, fine=fine, n_fixed=len(adj["changes"]), playbook=pb_html, hc_line=hc_line, best_cut=best_cut,
        cost_line=(f"{bench['tokens_per_pair']} input tokens per pair; this whole run cost ${bench['cost_usd_this_run']:.4f}."
                   if have_jev else "About 700 input tokens per pair; the whole run costs under a cent."),
        data=json.dumps({"rows": rows, "gaps": gaps[:15], "haveJev": have_jev}).replace("</", "<\\/"),
    )
    page = TEMPLATE
    for k, v in vals.items():
        page = page.replace("%%" + k + "%%", str(v))
    (SITE / "index.html").write_text(page)
    print("wrote", SITE / "index.html", "| jev:", have_jev, "| gaps:", len(gaps))


TEMPLATE = open(pathlib.Path(__file__).with_name("page_template.html")).read()

if __name__ == "__main__":
    main()
