# Golden-set annotation guide

Annotate the 200 rows in `data/golden_eval.csv` without looking at
`proposed_intent`, `proposed_route`, or `historical_reply`. The tweet text is
the only input available to the agent. The historical reply is retained for
later reply-quality judging, not intent labeling.

1. Assign exactly one `intent` from `src/taxonomy.py`.
2. Set `expected_route` to `auto_handle` only when a safe, generic public
   answer could solve the request without account lookup or transaction action.
   Otherwise set it to `escalate`.
3. Give a short `escalation_reason` for every escalation: `account_or_security`,
   `billing_or_order_action`, `repair_case_specific`, `sensitive_data`,
   `ambiguous`, or `high_emotion`.
4. Set `review_status=human_reviewed` and leave a note when you had to make a
   difficult call.

## Intent decision rules

| Intent | Include | Exclude |
|---|---|---|
| `account_access_security` | Apple Account sign-in, verification, lockout, suspected compromise | generic app malfunction without account access |
| `billing_subscription` | charge, refund, payment method, subscription entitlement | delivery date for a hardware order |
| `order_delivery` | order placement, tracking, stock, delivery, trade-in | App Store purchase refund |
| `repair_service` | damage, diagnostics, warranty, repair appointment | nonphysical software fault |
| `device_technical_issue` | a device, app, service, or accessory does not work | “how do I…” with no reported failure |
| `how_to` | capability or setup instructions | account-specific action needed to complete the task |
| `feedback_complaint` | praise or complaint without an actionable product-support task | complaint plus a concrete technical/billing issue |
| `other` | too vague, non-Apple, or no supported task | use another label whenever a clear issue exists |

## Sampling note

`src.make_golden` draws a seed-fixed, stratified 200-row sample of direct
customer-to-AppleSupport exchanges: 25 each for account, billing, order, and
repair; 30 each for device issue and how-to; and 20 each for feedback and
other. Stratification uses a transparent proposal rule only to ensure coverage.
Human annotators label independently and proposal columns must remain hidden
while they do so. A second reviewer should adjudicate a 40-row (20%) random
subset; record disagreements in `review_notes`.
