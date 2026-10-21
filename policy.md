# Complaint triage policy (v1)

The triage model gets this file in its prompt for the "with policy" condition. Labels in `labels.csv` were made against the same text.

## Categories

Pick the one main problem: the thing the customer most wants fixed. If several apply, pick the one causing ongoing money or legal harm.

| key | use when | routed to |
| --- | --- | --- |
| `rc_transfer` | Ownership/RC not transferred after a sale or purchase, NOC, challans or FASTag charges arriving after the sale, RC card not received | Documentation & RTO |
| `price_after_inspection` | Seller says the quote was cut after inspection, offer renegotiated at the hub, or unfair deductions from the sale price | Seller pricing & inspection |
| `refund_payment` | Token/booking amount not refunded, sale proceeds not paid, double charge, any money owed by Cars24 not received | Payments |
| `vehicle_condition` | Defects found after purchase, misrepresented condition, warranty or return claim refused, inspection/PDI service done badly | Warranty & after-sales |
| `loan_finance` | Car loan, EMI, foreclosure, loan-closure NOC, deductions by the financier, Loans24 | Loans24 |
| `support_conduct` | The main issue is the support itself: no response, spam or harassing calls, rude or misleading staff, with no other problem above | CX escalations |
| `other` | Anything else (e.g. job offers, scams using the Cars24 name) | CX escalations |

## Urgency

Apply these in order.

- **high** if any of these holds:
  - (a) a safety risk from the car (brakes, steering, airbags, engine or overheating failure while driving);
  - (b) the customer faces ongoing legal or financial liability: challans, police, or insurance claims tied to a car they no longer own;
  - (c) money owed to the customer has been held for 30+ days;
  - (d) a legal notice, police complaint, or consumer-court filing is made or threatened.
- **low** if no money is held and there is no ongoing harm: a price disagreement before the sale, unwanted calls, rude staff, or general dissatisfaction.
- **medium** otherwise.

## Reply rules

The reply is a first public response, 2–4 sentences.

- Acknowledge the specific problem in plain words, not "we regret the inconvenience" alone.
- Give one concrete next step and ask for the appointment or booking ID.
- **Never** promise an outcome or amount ("we will refund", "you will get Rs.X").
- **Never** promise a deadline ("within 48 hours", "by tomorrow").
- **Never** admit legal fault ("this is our mistake, we will compensate").
- **Never** ask for an OTP, password, PIN or full card number, and never repeat the customer's phone number, registration number or name.
