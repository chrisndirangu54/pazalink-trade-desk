# Bodaless → PazaLink feature integration (sandbox)

Source: user-supplied `Bodaless_Pitch_Lisk_Mobile_AI(2).pptx`, slides 1–9. This extension is a **simulation**, not a working payment, FX, credit or chain service. It adds API scaffolding while preserving the existing PayPal/Nebius prototype. `/api/bodaless/capabilities` reports live integration status honestly.

## Features implemented as demonstrable **in-process simulations**
| Bodaless pitch feature | PazaLink route | Limits |
|---|---|---|
| KES→UGX/TZS/RWF corridor estimates | POST `/api/bodaless/quotes` | Fictional sample rates; no live market feed |
| USSD/app/SMS/voice/WhatsApp send journey | POST `/api/bodaless/transfers` | Creates an intent only; no mobile-money call |
| Border escrow for trade goods | POST `/api/bodaless/escrows`, `/{id}/actions` | Strict state machine, no funds locked |
| Trader buy/sell marketplace | POST/GET `/api/bodaless/trade/listings` | Tenant-only listings; no public matching |
| OTP/voice-verify journey | `/verification/challenges` and confirm | No call or SMS sent; no identity verified |
| RateLock (24-hour proposal) | POST `/api/bodaless/rate-locks` | Not guaranteed or hedged |
| Cross-border chama proposal | POST `/api/bodaless/chamas` | No pooled funds or bulk payout |
| Trade Passport | POST `/api/bodaless/trade-passports` | No KYC, DID, blockchain NFT or credit eligibility |
| Odoo posting concept | GET `/api/bodaless/accounting/odoo-preview` | Unposted accounting draft only |
| Swahili/English conversational risk tips | POST `/api/bodaless/assistant` | Transparent rules fallback; not a language model |
| Feature-channel availability | GET `/api/bodaless/capabilities` | Marks missing integrations not connected |

All authenticated demo objects are keyed by the **Firebase principal** in ephemeral process memory. This is suitable only for local test sessions, not multi-worker servers or persistence. The API is automatically documented at `/docs` when running the FastAPI application.

## External integrations to build/test **before claiming feature completeness**
1. **Africa's Talking:** allocate an actual USSD shortcode (the pitch's `*384*7#` is illustrative, not provisioned here); implement signed webhooks, short sessions, SMS and outbound calls, transcription/localization, throttling, and consent.
2. **Payaza:** obtain permitted merchant API keys, review supported countries/currencies/settlement rails and sandbox specifications; implement idempotent collection, FX quote, payouts and signed webhook verification. No claim that its API provides a particular rate or route until verified.
3. **Safaricom Daraja, Airtel Money, MTN MoMo:** provider onboarding, callback verification, fees, reversals, recipient/agent payout testing, mobile-money reconciliation and regulatory approval.
4. **Lisk:** deploy and audit an escrow smart contract on a testnet, verify onchain event confirmations, distinguish *escrow* from *proof-only hashes*, and confirm lawful custodial model before production.
5. **PayPal/card/bank (RTGS/SWIFT):** preserve the existing PayPal sandbox integration; assess provider permissions and availability for the specific Kenya–EAC/diaspora corridor before any live collection or disbursement.
6. **Odoo/tax:** create consented, idempotent journal adapters; tax receipts and jurisdiction-specific KRA/TRA reporting require professional/legal checks.
7. **AI and trade signals:** connect authorized market-price feeds, product supply/demand data, Nebius model, human-readable grounding and uncertainty; no automated credit or fraud decisions without data and safeguards.
8. **KYC and merchant passport:** obtain permissioned identity verification, a compliant treatment of personal data, and appropriate credit risk governance. A blockchain token is **not** evidence of completed KYC.
9. **Mobile UI and accessibility:** implement Flutter mobile app, secure wallet/history/receipts, merchant onboarding, consent-based voice workflows, and error/recovery journeys.
10. **Chama and RateLock:** actual pooled wallets, hedging, rate guarantees and agent arbitration need licensed providers and binding product terms.

### Local quickstart

```bash
pip install -r requirements.txt
uvicorn app:app --reload
pytest -q tests/test_bodaless.py
```

Firebase identity is required for business endpoints. For **offline test clients only**, the tests override the Firebase dependency. To view a generated code during local testing, set `BODALESS_SHOW_DEMO_OTP=true`; never enable this in a deployed environment. Real endpoints default to showing **no OTP** and never deliver it.

### Example escrow demonstration

1. POST `/api/bodaless/escrows` with buyer, seller, description, amount, currency and channel.
2. POST `/api/bodaless/escrows/{id}/actions` with `{"action":"simulate-funding"}`.
3. Repeat with `{"action":"confirm-delivery"}`, then `{"action":"simulate-release"}`.
4. Check response: `funds_custodied=false` and `blockchain_tx=null` at all steps.

## Security and compliance boundaries
- All cash transfers, ledger settlement, FX execution and chain operations are **disabled**; nothing is collected or disbursed.
- Demo code confirmation validates only knowledge of a generated code, **not identity** or a real voice biometric.
- Escrow states are simulation only and have no economic or blockchain effect.
- Avoid collecting national IDs, true customer payment details, voiceprints, passports or secrets in demo records.
- For production: persist tenant-isolated data, design a double-entry ledger, authorization per counterparty, least-privilege roles, strong idempotency/replay controls, signed webhooks, audited custody, dispute policy, data protection, FX/remittance and AML/CFT compliance.
