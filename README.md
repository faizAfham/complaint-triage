# Complaint Triage

Sorts a used-car customer complaint into a category, an urgency and an owning team, and drafts a first reply that promises nothing support can't back up. It is evaluated on all 97 public Cars24 complaints on consumercomplaints.in. Not affiliated with Cars24.

## The story

**It started with an application.** Before applying to Cars24, I wanted to see the company from the customer's side, so I read every public complaint I could find: 97 on consumercomplaints.in, plus Trustpilot and Voxya.

**The same few problems kept coming up.**
- A seller hands over the car, gets paid, and months later is still getting traffic challans, because the RC was never moved out of their name.
- A buyer waits weeks for a token refund.

Each complaint was different in its details but the same underneath. Yet the public replies were almost all one template: "please share your details, our team will reach out."

**That looked like a routing problem, not a people problem.** Cars24 already runs 45+ AI agents across support, CRM and voice, so the question isn't whether an LLM should read these complaints. The question is whether it can be trusted to. Two things matter:
- It has to send each complaint to the right team. An RC problem that lands with payments just waits longer.
- It has to reply **safely**. In public, a reply that says "we'll refund you in 48 hours" or repeats the customer's registration number creates a second problem.

**So I built the smallest thing that answers that question.** It is a triage tool: complaint in → category, urgency, owning team and a first reply out. I wrote the rules a support lead would give a new hire (`policy.md`) *before* looking at any model output, so the policy could not be tuned to the test.

**Then I measured it three ways:** keyword rules (what a quick script would do), the LLM on its own, and the LLM with the policy.

| | Category acc. | Urgent cases caught | Replies breaking a rule |
| --- | --- | --- | --- |
| Keyword rules | 52% | 13 of 29 | – |
| LLM, no policy | 79% | 27 of 29 | 14 of 97 |
| LLM + policy | **89%** | **28 of 29** | **0 of 97** |

**What surprised me.** The LLM on its own was already good at sorting. Its real weakness was the reply:
- 13 of its replies repeated the customer's registration number back in public.
- One promised "an update within 24 hours."

Giving it the policy didn't just raise accuracy. It removed every one of those mistakes. It also got the model to ask for a booking ID in 98% of replies (44% before), and that is the one thing support actually needs to act.

**What still doesn't work.** Urgency. The model almost never misses a truly urgent case (28 of 29), but it over-reacts: it called 35 of the 56 medium complaints "high." In a real queue that is the costlier failure. If everything is urgent, nothing is. My next change would make the policy stricter: "money held 30+ days" should count only when the complaint states it, not when the model infers it.

**How far to trust these numbers.**
- **The labels are one careful reading, not Cars24's ground truth.** A separate labeller applied the policy without seeing any model output, and flagged 40 of 97 as genuinely ambiguous. On the 57 clear-cut cases, the LLM with the policy gets 96.5% of categories right.
- **The reply checker is regex rules with tests.** It catches common phrasings, so a cleverly paraphrased promise could slip through. The upgrade is an LLM judge spot-checked against it.
- **The complaints are self-selected and mostly from 2019–2023.**

## Run

```bash
python3 collect.py 5          # fetch the public complaints -> data/ (gitignored: contains names, phone and reg. numbers)
python3 triage.py "Sold my car 3 months ago, RC still not transferred" --policy
python3 eval.py --selftest    # reply checker + baseline tests, no LLM
python3 eval.py               # runs both LLM conditions (cached), writes results.json
```

Needs only the Python 3 standard library. LLM: set `ANTHROPIC_API_KEY`, or have the `claude` CLI installed. Model: `TRIAGE_MODEL` (default `claude-haiku-5-5`).

## Files

- `policy.md`: the categories, urgency rules and reply rules.
- `labels.csv`: complaint id, category, urgency, confidence, short reason. Complaint URLs are the ids on consumercomplaints.in.
- `results.json`: the metrics plus per-complaint predictions and rule hits. No complaint text and no reply text.
