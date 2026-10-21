# PazaLink implementation and verification status

Updated: 2026-10-22.

## Implemented in repository
- Responsive Trade Desk with visibly **fictional** payment records.
- Server-side PayPal REST sandbox order creation and capture endpoints.
- Nebius Token Factory AI analysis endpoint when a Nebius API key is present.
- Explicit rules-only fallback when model credentials are absent.
- Basic input validation and automated offline tests in GitHub Actions.

## Requires configured credentials and external verification
- **PayPal**: Test order creation, buyer approval and capture using separate PayPal sandbox buyer/seller accounts. An order must be approved by its buyer before capture. Check status and transaction IDs against PayPal sandbox dashboard. Never describe an unapproved order as settled.
- **Nebius**: Configure token and confirm actual deployed model ID, response parsing and latency. The model response is guidance, not proof or authority to move funds.
- **Deployment**: Protect all environment secrets, restrict CORS, set HTTPS, validate deployment health and logs. Public demo must not allow arbitrary visitors to capture shared sandbox orders.

## Not implemented (do not claim otherwise)
- Live M-Pesa STK or Daraja, Airtel Money, MTN MoMo, Payaza FX or payouts.
- Africa's Talking USSD/SMS, QR invoices, real merchant authentication or KYC.
- Celo/Lisk smart contracts, escrow, custodial wallets, disputes, exchange settlement.
- Odoo sync, real reconciliation records, ledger persistence, audit log or payments compliance.
- PayPal webhooks, idempotent fulfillment, live payouts or production money movement.

## Recommended build sequence
1. Add users, per-user isolation, authorization, persistent invoices and append-only audit log.
2. Complete PayPal sandbox buyer-approval UX, webhooks with signature checks, replay protection and reconciliation.
3. Integrate actual Nebius model with schema-validated outputs and human review.
4. Implement Africa's Talking USSD/SMS simulator, then sandbox flows and approved PSP rails.
5. Prototype escrow only after custody, dispute, contract audit and regulatory review.
6. Run security and user acceptance tests before claiming production readiness.

## Safety
This repository is a prototype and must remain sandbox only. Real remittance, payments, FX and custody require licensing/compliance review, provider agreements, privacy and security assessment, and transaction monitoring.
