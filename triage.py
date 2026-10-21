"""Triage a Cars24 customer complaint: category, urgency, team, and a safe first reply.

Usage: python3 triage.py "complaint text" [--policy]
LLM: Anthropic API if ANTHROPIC_API_KEY is set, else the local `claude` CLI.
"""
import json, os, re, subprocess, sys, urllib.request
from pathlib import Path

MODEL = os.environ.get("TRIAGE_MODEL", "claude-haiku-5-5")
POLICY = (Path(__file__).parent / "policy.md").read_text()
TEAMS = {
    "rc_transfer": "Documentation & RTO",
    "price_after_inspection": "Seller pricing & inspection",
    "refund_payment": "Payments",
    "vehicle_condition": "Warranty & after-sales",
    "loan_finance": "Loans24",
    "support_conduct": "CX escalations",
    "other": "CX escalations",
}
URGENCY = ("high", "medium", "low")

PROMPT = """You triage customer complaints about Cars24, an Indian used-car platform.
{policy}
Complaint:
\"\"\"{text}\"\"\"

Reply with JSON only, no prose:
{{"category": "<one of: {cats}>",
  "urgency": "<high | medium | low>",
  "reply": "<a 2-4 sentence first public reply from Cars24 support>"}}"""


def build_prompt(text, use_policy):
    policy = f"\nFollow this policy:\n{POLICY}\n" if use_policy else ""
    return PROMPT.format(policy=policy, text=text[:4000], cats=", ".join(TEAMS))


def call_llm(prompt):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({"model": MODEL, "max_tokens": 500,
                             "messages": [{"role": "user", "content": prompt}]}).encode(),
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=60))["content"][0]["text"]
    # ponytail: CLI fallback so it runs with no API key; ~5s/call, use the API for anything bigger
    return subprocess.run(["claude", "-p", "--model", MODEL, prompt], capture_output=True, text=True, timeout=180).stdout


def triage(text, use_policy=False):
    raw = call_llm(build_prompt(text, use_policy))
    try:
        out = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except ValueError:
        out = {}
    if out.get("category") not in TEAMS:
        out["category"] = "invalid"
    if out.get("urgency") not in URGENCY:
        out["urgency"] = "invalid"
    out["team"] = TEAMS.get(out["category"], "invalid")
    out.setdefault("reply", "")
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    text = args[0] if args else "Sold my car 3 months ago, RC still not transferred and I keep getting challans."
    print(json.dumps(triage(text, "--policy" in sys.argv), indent=2, ensure_ascii=False))
