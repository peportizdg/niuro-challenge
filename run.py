"""Corre todo: motor de keywords -> reviewer -> evaluación -> impacto en crédito.
Escribe output/report.md (lo que se lee) y output/flags.json (la cola del underwriter).

Uso: python3 run.py [transactions.json] [carpeta de salida]
"""
import json
import re
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import credit
import engine
import reviewer
from labels import HIGH_RISK, is_revenue

ROOT = Path(__file__).parent
PRICE_PER_MTOK = {"input_tokens": Decimal(4), "output_tokens": Decimal(20)}  # claude-opus-5-5, USD


def main(path=ROOT / "data" / "transactions.json", out_dir=ROOT / "output"):
    path, out_dir = Path(path), Path(out_dir)
    data = json.loads(path.read_text(), parse_float=Decimal)
    txns = data["transactions"] if isinstance(data, dict) else data
    names = {a["account_id"]: a["name"] for a in data.get("accounts", [])} if isinstance(data, dict) else {}
    by_business = defaultdict(list)
    for t in sorted(txns, key=lambda t: (t["account_id"], t["date"])):
        t["amount"] = Decimal(t["amount"])  # por si llega como int
        by_business[names.get(t["account_id"], t["account_id"])].append(t)

    before = {t["transaction_id"]: engine.label(t["name"]) for t in txns}
    flags, failed, dropped, usage = {}, 0, 0, defaultdict(int)
    for name, items in by_business.items():
        r = reviewer.review(name, items, before)
        flags.update(r.flags)
        failed += r.failed
        dropped += r.dropped
        for k, v in r.usage.items():
            usage[k] += v
    after = reviewer.apply(txns, before, flags)
    approved = reviewer.apply(txns, before, flags, approved=True)
    cost = sum(Decimal(usage[k]) * p / 1_000_000 for k, p in PRICE_PER_MTOK.items())
    confident = sum(f["confidence"] >= reviewer.MIN_CONFIDENCE for f in flags.values())
    auto = sum(after[t] != before[t] for t in after)

    # truth.json solo existe para los datos sintéticos; con datos ajenos se salta la evaluación.
    truth_path = path.with_name("truth.json")
    truth = json.loads(truth_path.read_text()) if truth_path.exists() else None

    lines = [f"# Reviewer report: {path.name}", "",
             f"- Transactions: {len(txns)} across {len(by_business)} businesses",
             f"- Model: {reviewer.MODEL}. Chunks not reviewed: {failed}. Invalid model flags dropped: {dropped}",
             f"- Model calls: {usage['input_tokens']:,} input + {usage['output_tokens']:,} output tokens, "
             f"about US${cost:.2f} at list price",
             f"- Flags: {len(flags)}. Auto-applied: {auto}. Waiting for an underwriter because they would "
             f"raise the offer: {confident - auto}. Below confidence {reviewer.MIN_CONFIDENCE}: {len(flags) - confident}",
             "- Labels compared below: `engine`, `reviewed` (auto-applied flags only), `approved` "
             "(an underwriter accepts every confident flag) and `truth`"]
    if truth:
        lines += quality_report(by_business, before, flags, after, approved, truth)
    lines += credit_report(by_business, before, after, approved, truth)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.md").write_text("\n".join(lines) + "\n")
    (out_dir / "flags.json").write_text(json.dumps(queue(by_business, before, flags, after), indent=1))
    print(f"Report: {out_dir / 'report.md'}")


def queue(by_business, before, flags, after):
    rows = []
    for name, items in by_business.items():
        for t in items:
            f = flags.get(t["transaction_id"])
            if f:
                rows.append({
                    "transaction_id": t["transaction_id"], "business": name, "date": t["date"],
                    "amount": str(t["amount"]), "description": t["name"],
                    "engine": label_dict(t, before[t["transaction_id"]]),
                    "proposed": label_dict(t, (f["group"], f["business"])),
                    "confidence": f["confidence"], "reason": f["reason"],
                    "applied": after[t["transaction_id"]] != before[t["transaction_id"]],
                })
    return rows


def label_dict(t, lab):
    # revenue lo calcula el código, nunca el modelo.
    return {"group": lab[0], "business": lab[1], "revenue": is_revenue(t["amount"], *lab)}


def moves_features(t, lab):
    """Lo que de una etiqueta llega a las features: si un error no cambia esto, no cambia la oferta."""
    group, business = lab
    debit = t["amount"] > 0
    return (is_revenue(t["amount"], group, business), group if group in ("nsf", "overdraft") else None,
            debit and group == "active_advance", debit and group in HIGH_RISK)


def quality_report(by_business, before, flags, after, approved, truth):
    rows = {k: [] for k in ["correct fix", "wrong fix", "false flag", "missed"]}
    counts = defaultdict(lambda: [0, 0])  # categoría -> [todas, las que mueven features]
    real_labels = {tid: (v["group"], v["business"]) for tid, v in truth.items()}
    revenue = []
    for name, items in by_business.items():
        revenue.append((name, *(credit.features(items, labels)["monthly_revenue"]
                                for labels in (real_labels, before, after, approved))))
        for t in items:
            tid = t["transaction_id"]
            real = real_labels[tid]
            f = flags.get(tid)
            proposed = (f["group"], f["business"]) if f else None
            if f and before[tid] == real:
                kind = "false flag"
            elif f:
                kind = "correct fix" if proposed == real else "wrong fix"
            elif before[tid] != real:
                kind = "missed"
            else:
                continue
            matters = moves_features(t, before[tid]) != moves_features(t, real)
            counts[kind][0] += 1
            counts[kind][1] += matters
            if kind != "missed" or matters:
                rows[kind].append((name, t, before[tid], real, f))

    errors = [counts[k][i] for k in ("correct fix", "wrong fix", "missed") for i in (0, 1)]
    out = ["", "## Reviewer quality (against data/truth.json)", "",
           "Every valid flag counts here, applied or not.", "",
           "| | all | that move a credit feature |", "|---|---:|---:|",
           f"| Engine errors | {sum(errors[0::2])} | {sum(errors[1::2])} |",
           *(f"| {k} | {counts[k][0]} | {counts[k][1]} |" for k in ("correct fix", "wrong fix", "missed")),
           f"| false flag (engine was right) | {counts['false flag'][0]} | {counts['false flag'][1]} |"]

    tagged = defaultdict(list)
    for name, items in by_business.items():
        for t in items:
            if truth[t["transaction_id"]]["tag"]:
                tagged[truth[t["transaction_id"]]["tag"]].append((name, t))
    out += ["", f"Hard negatives (tag `looks_wrong`): {sum(t['transaction_id'] in flags for _, t in tagged['looks_wrong'])}"
            f" of {len(tagged['looks_wrong'])} flagged.", "",
            "### Monthly revenue per business", "",
            "| business | true | engine error | reviewed error | approved error |", "|---|---:|---:|---:|---:|"]
    for name, real, *versions in revenue:
        out.append(f"| {name} | {real:,.0f} | " + " | ".join(f"{v - real:+,.0f}" for v in versions) + " |")
    out.append("| **total absolute error** | | "
               + " | ".join(f"{sum(abs(row[i] - row[1]) for row in revenue):,.0f}" for i in (2, 3, 4)) + " |")

    out += ["", "### Prompt injection attempts", ""]
    for name, t in tagged["injection"]:
        f = flags.get(t["transaction_id"])
        real = truth[t["transaction_id"]]
        out.append(f"- {name}: `{cell(t['name'])}` engine={fmt(before[t['transaction_id']])} "
                   f"truth={fmt((real['group'], real['business']))} -> "
                   + (f"flagged as {fmt((f['group'], f['business']))} ({f['confidence']}): {cell(f['reason'])}"
                      if f else "not flagged"))

    for kind, title in (("false flag", "False flags"), ("wrong fix", "Flagged with the wrong label"),
                        ("missed", "Missed errors that move a credit feature"), ("correct fix", "Correct fixes")):
        out += ["", f"### {title}", "", "| business | n | description | engine | truth | flag |", "|---|---:|---|---|---|---|"]
        for (name, desc, eng, real, prop), group in similar(rows[kind]).items():
            f = group[0][4]
            flag = f"{fmt(prop)} ({f['confidence']}): {cell(f['reason'])}" if f else ""
            out.append(f"| {name} | {len(group)} | `{cell(desc)}` | {fmt(eng)} | {fmt(real)} | {flag} |")
    return out


def similar(rows):
    # Agrupa filas que solo difieren en números (IDs de traza, fechas) para que la tabla se pueda leer.
    groups = defaultdict(list)
    for name, t, eng, real, f in rows:
        prop = (f["group"], f["business"]) if f else None
        groups[(name, re.sub(r"\d+", "#", t["name"]), eng, real, prop)].append((name, t, eng, real, f))
    return groups


def cell(text):
    # Texto de la contraparte o del modelo: que no rompa la tabla markdown.
    return " ".join(text.replace("|", "/").replace("`", "'").split())


def fmt(lab):
    return f"{lab[0] or 'none'}/{'biz' if lab[1] else 'personal'}"


def credit_report(by_business, before, after, approved, truth):
    real = {tid: (v["group"], v["business"]) for tid, v in truth.items()} if truth else None
    versions = [("engine", before), ("reviewed", after), ("approved", approved)] + ([("truth", real)] if real else [])
    out = ["", "## Credit features and offer", "",
           "| business | labels | revenue / deposits | NSF | overdraft | high risk / debits "
           "| monthly revenue | funder daily | offer |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, items in by_business.items():
        for version, labels in versions:
            f = credit.features(items, labels)
            out.append(f"| {name} | {version} | {f['revenue_share']:.0%} | {f['nsf']} | {f['overdraft']} "
                       f"| {f['high_risk_share']:.1%} | {f['monthly_revenue']:,.0f} | {f['funder_daily']:,.0f} "
                       f"| {f['offer']:,.0f} |")
    if not real:
        return out

    mean_offer = sum(credit.features(items, real)["offer"] for items in by_business.values()) / len(by_business)
    out += ["", "## Mislabel sensitivity (true labels, corrupted on purpose; 50 runs per business)", "",
            f"Mean true offer: {mean_offer:,.0f}. Columns are mean absolute changes per business, "
            "except the last one, which keeps the sign. `random group` mislabels that share of all "
            "transactions; each named error mislabels that share of the transactions it can happen to.", "",
            "| mislabel | rate | revenue share (pp) | NSF count | high risk share (pp) | offer | offer, signed |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    cases = [("random group", rate, None) for rate in (0.02, 0.05, 0.10)]
    cases += [(error, 0.05, error) for error in credit.ERROR_TYPES]
    for label, rate, error in cases:
        m = credit.mislabel_sweep(by_business, real, rate, error)
        out.append(f"| {label} | {rate:.0%} | {m['revenue_share'] * 100:.1f} | {m['nsf']:.2f} "
                   f"| {m['high_risk_share'] * 100:.1f} | {m['offer']:,.0f} | {m['offer_signed']:+,.0f} |")
    return out


if __name__ == "__main__":
    main(*sys.argv[1:])
