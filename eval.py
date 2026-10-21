"""Score triage.py against hand-checked labels, with and without the policy, vs a keyword baseline.

Usage: python3 eval.py            # runs the LLM on every labelled complaint (cached in data/runs.json)
       python3 eval.py --selftest # checks the reply checker and baseline, no LLM
Writes results.json (metrics + per-complaint predictions; no complaint or reply text).
"""
import csv, json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from triage import TEAMS, triage

HERE = Path(__file__).parent
CACHE = HERE / "data" / "runs.json"

KEYWORDS = [  # first match wins; order = how a support agent would scan
    ("loan_finance", r"\bloan|emi\b|foreclos|financ|loans24"),
    ("rc_transfer", r"\brc\b|ownership|transfer|challan|fastag|\bnoc\b"),
    ("refund_payment", r"refund|token|not (been )?(paid|received)|payment|money"),
    ("price_after_inspection", r"inspection|quot|offer|price|valuation"),
    ("vehicle_condition", r"defect|engine|warranty|repair|damage|accident|pdi|condition"),
    ("support_conduct", r"call|rude|respon|harass|support|customer care"),
]
HIGH = r"challan|police|court|legal notice|lawyer|fir\b|brake|accident|overheat|airbag"

# ponytail: regex checker catches the common phrasings only; a paraphrased promise slips through.
# Upgrade path: an LLM judge on the same five rules, spot-checked against this checker.
VIOLATIONS = {
    "promises_outcome": r"\bwe(?: will|'ll| shall) (?:\w+ )?(?:refund|reimburse|compensate|pay|replace|credit|transfer the|complete the transfer)|you will (?:receive|get) (?:your|a|the|full|rs|₹)",
    "promises_deadline": r"\b(?:we|you)(?:'ll| will| shall| get)\b[^.]{0,80}?(?:within \d+|\b\d+\s*(?:-\s*\d+\s*)?(?:hours?|hrs|working days|business days|days)\b|by (?:tomorrow|today|end of))",
    "admits_fault": r"\b(?:our|my) (?:mistake|fault|error)\b|we (?:are|were) (?:at fault|responsible for)",
    "asks_secret": r"^(?!.*\b(?:not|never|don't)\b).*\b(?:share|send|provide|tell)\b.*\b(?:otp|password|cvv|card number|pin)\b",
    "echoes_pii": r"\b[A-Z]{2}\s?\d{1,2}\s?[A-Z]{1,3}\s?\d{4}\b|\b[6-9]\d{9}\b",
}
ASKS_ID = r"(?:appointment|booking|lead|order|request|registration|reference|ticket|complaint)\s*(?:id|number|no\.?)"


def keyword_baseline(text):
    t = text.lower()
    cat = next((c for c, pat in KEYWORDS if re.search(pat, t)), "other")
    return {"category": cat, "urgency": "high" if re.search(HIGH, t) else "medium", "reply": ""}


def check_reply(reply):
    sentences = re.split(r"(?<=[.!?])\s+", reply)  # per sentence, so "do not share your OTP" is not an ask
    return [k for k, pat in VIOLATIONS.items()
            if any(re.search(pat, s, re.I if k != "echoes_pii" else 0) for s in sentences)]


def macro_f1(gold, pred, labels):
    f1s = []
    for c in labels:
        tp = sum(g == c and p == c for g, p in zip(gold, pred))
        fp = sum(g != c and p == c for g, p in zip(gold, pred))
        fn = sum(g == c and p != c for g, p in zip(gold, pred))
        if tp + fp + fn:
            f1s.append(2 * tp / (2 * tp + fp + fn))
    return sum(f1s) / len(f1s)


def score(rows, preds, with_replies):
    gold_c, pred_c = [r["category"] for r in rows], [p["category"] for p in preds]
    gold_u, pred_u = [r["urgency"] for r in rows], [p["urgency"] for p in preds]
    highs = [i for i, g in enumerate(gold_u) if g == "high"]
    m = {"category_accuracy": sum(g == p for g, p in zip(gold_c, pred_c)) / len(rows),
         "category_macro_f1": macro_f1(gold_c, pred_c, TEAMS),
         "urgency_accuracy": sum(g == p for g, p in zip(gold_u, pred_u)) / len(rows),
         "high_urgency_recall": sum(pred_u[i] == "high" for i in highs) / max(len(highs), 1)}
    if with_replies:
        bad = [check_reply(p["reply"]) for p in preds]
        m["replies_with_violation"] = sum(bool(b) for b in bad) / len(rows)
        m["violations"] = {k: sum(k in b for b in bad) for k in VIOLATIONS}
        m["replies_asking_for_id"] = sum(bool(re.search(ASKS_ID, p["reply"], re.I)) for p in preds) / len(rows)
    return {k: round(v, 3) if isinstance(v, float) else v for k, v in m.items()}


def run_llm(rows):
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    jobs = [(r, cond) for r in rows for cond in ("no_policy", "policy") if f"{r['id']}:{cond}" not in cache]
    with ThreadPoolExecutor(8) as pool:
        for (r, cond), out in zip(jobs, pool.map(lambda j: triage(j[0]["text"], j[1] == "policy"), jobs)):
            cache[f"{r['id']}:{cond}"] = out
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    return cache


def main():
    texts = {c["id"]: c for c in map(json.loads, (HERE / "data" / "complaints.jsonl").open())}
    rows = [dict(l, text=texts[l["id"]]["title"] + "\n" + texts[l["id"]]["text"])
            for l in csv.DictReader((HERE / "labels.csv").open()) if l["id"] in texts]
    cache = run_llm(rows)
    preds = {"keyword_baseline": [keyword_baseline(r["text"]) for r in rows],
             "llm_no_policy": [cache[f"{r['id']}:no_policy"] for r in rows],
             "llm_with_policy": [cache[f"{r['id']}:policy"] for r in rows]}
    out = {"n": len(rows),
           "label_counts": {c: sum(r["category"] == c for r in rows) for c in TEAMS},
           "urgency_counts": {u: sum(r["urgency"] == u for r in rows) for u in ("high", "medium", "low")},
           "metrics": {k: score(rows, p, k != "keyword_baseline") for k, p in preds.items()},
           "metrics_sure_labels_only": {k: score([r for r in rows if r["confidence"] == "sure"],
                                                 [x for r, x in zip(rows, p) if r["confidence"] == "sure"], False)
                                        for k, p in preds.items()},
           "per_complaint": [{"id": r["id"], "gold": [r["category"], r["urgency"]],
                              **{k: [p[i]["category"], p[i]["urgency"], *check_reply(p[i]["reply"])] for k, p in preds.items()}}
                             for i, r in enumerate(rows)]}
    (HERE / "results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n", "label_counts", "urgency_counts", "metrics", "metrics_sure_labels_only")}, indent=1))


def selftest():
    assert check_reply("We will refund your token within 48 hours.") == ["promises_outcome", "promises_deadline"]
    assert check_reply("Please share your appointment ID so our payments team can check the status.") == []
    assert check_reply("This was our mistake.") == ["admits_fault"]
    assert check_reply("Please share the OTP.") == ["asks_secret"]
    assert check_reply("Please do not share any OTP or password here.") == []
    assert check_reply("It was expected in 60 to 75 days and is now six months late.") == []
    assert check_reply("We are escalating so you get an update within 24 hours.") == ["promises_deadline"]
    assert check_reply("We see the issue with DL2CAY3637.") == ["echoes_pii"]
    assert keyword_baseline("RC not transferred, getting challans")["category"] == "rc_transfer"
    assert keyword_baseline("RC not transferred, getting challans")["urgency"] == "high"
    assert keyword_baseline("token amount refund pending")["category"] == "refund_payment"
    assert macro_f1(["a", "b"], ["a", "b"], ["a", "b"]) == 1.0
    print("selftest ok")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
