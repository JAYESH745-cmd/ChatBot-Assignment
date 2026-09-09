# Apple Support intent taxonomy

These eight labels were formed from recurring issue types in the direct
customer-to-AppleSupport slice. They deliberately represent the operational
next step—not a product ontology—and are kept small enough to annotate
consistently.

| Intent | Definition | Real slice example |
|---|---|---|
| `account_access_security` | Apple Account password, sign-in, verification, lockout, or suspected security issue | “It’s asking for a verification code … to my old number.” (`G015`) |
| `billing_subscription` | Charge, refund, payment, paid entitlement, or subscription issue | “You removed some paid apps … please refund me.” (`G001`) |
| `order_delivery` | Hardware order, shipment, stock, store pickup, delivery, or trade-in question | “Why is my order still ‘Preparing for Shipment’?” (`G002`) |
| `repair_service` | Damage, hardware repair, warranty, Genius Bar, or service scheduling | “Can I make a repair reservation for my MacBook online?” (`G043`) |
| `device_technical_issue` | Device, operating system, app, iCloud, or accessory does not work as expected | “Messages app keep closing.” (`G091`) |
| `how_to` | Safe general instructions about a capability, setting, or compatibility | “Where can I find liner notes?” (`G124`) |
| `feedback_complaint` | Praise, complaint, or feedback without a remaining actionable support task | “That worked, thank you!!” (`G173`) |
| `other` | Context-only, ambiguous, unsupported, or non-actionable text | “Messages from other people.” (`G006`) |

Boundary rule: when a message reports a failure and asks “how do I fix it?”,
label it `device_technical_issue`; reserve `how_to` for capability/settings
questions without a reported fault. If account access, money, a specific order,
or repair action is required, use the corresponding operational intent even if
technical symptoms are also present.
