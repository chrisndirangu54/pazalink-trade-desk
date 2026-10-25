# PazaLink Trade Desk

An AI-assisted payment and reconciliation workspace for East African cross-border traders. This repository is a new prototype built for the PayPal AI Hackathon and the Nebius × NVIDIA Global AI Hackathon.

## Current status

- The interface runs with clearly labeled synthetic sample transactions.
- PayPal sandbox order creation and guarded capture are implemented server-side. They require sandbox credentials, a private order-signing secret and Firebase sign-in. Capture remains disabled by default. A genuine fictional USD 1.00 order was approved in the generated sandbox buyer browser and captured: order `5XL09715K7475635L`, capture `4J214726CW1053453`. Repeating the adapter request reconciled the same capture. This was a direct adapter test; it did not exercise the complete authenticated payment UI.
- AI review calls Nebius Token Factory using NVIDIA Nemotron when `NEBIUS_API_KEY` is configured. Without it, the backend returns a transparent local rules demo; this fallback is not a model inference.
- No API keys or personal payment data are included in this repository.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`. Protected provider and invoice features require Firebase frontend configuration and sign-in; see `docs/FIREBASE.md`. To enable PayPal order creation, set `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` from a PayPal **sandbox** application. To enable the required NVIDIA model path, set `NEBIUS_API_KEY`; the default model is `nvidia/Nemotron-3_5-Lightning`, listed in the official [Nebius Nemotron cookbook](https://github.com/nebius/token-factory-cookbook/tree/main/models/nemotron). Actual availability and inference still need a live account test.

### PayPal sandbox approval and capture

Set `PAYPAL_ORDER_SIGNING_SECRET` to a privately generated random value of at least 32 characters; keep it on the server. For example, run `python -c "import secrets; print(secrets.token_urlsafe(32))"` and save the result in your private environment. Set `ENABLE_SANDBOX_CAPTURE=true` only for controlled sandbox testing. Use separate sandbox seller and buyer accounts.

After Firebase sign-in, create an order, follow **Approve in PayPal sandbox**, then return and choose **Check approval and capture sandbox order**. The server requires a signed one-hour receipt bound to your Firebase UID, order ID, reference and amount. It fetches the order directly from PayPal and checks buyer approval and the matching USD amount before capture. Stable idempotency keys protect retries; an already-completed order is reconciled without a second capture request. Only a matching `COMPLETED` processor capture is displayed as confirmed. Pending, mismatched and failed captures remain unconfirmed. No fictional ledger row is automatically marked paid.

An expired receipt cannot capture an order. Rotate the signing secret to invalidate outstanding receipts. Webhooks, durable fulfillment and production settlement are outside this prototype. See the official [PayPal capture API](https://developer.paypal.com/api/orders/v2/orders-capture) for approval and idempotency behavior.

### Local UI demonstration without credentials

PowerShell:

```powershell
$env:ENABLE_LOCAL_RULES_DEMO='true'
python -m uvicorn app:app --host 127.0.0.1 --port 8788
```

Open `http://127.0.0.1:8788`, select a fictional transaction, then choose **Try local rules sandbox**. This calls local rules only, even if a model key is configured. It never writes Firebase invoices, invokes Nebius, or creates payments. It is disabled by default and rejects remote peers, non-local hostnames and cross-origin requests. It does not unlock protected integration endpoints or replace a qualifying Nebius/PayPal demonstration.

The authenticated Nebius endpoint validates complete JSON output before displaying it. Malformed, truncated or refused responses fail visibly with HTTP 502 instead of silently becoming a successful fallback. The model's action text cannot authorize payment; the server always requires human review. A configured credential is not proof of a working integration.

## Safety and scope

This prototype does not initiate live payments. PayPal endpoints are hard-wired to the sandbox. AI output is decision support only: it does not execute transfers, make credit decisions, or verify geology, identity, invoices, or merchant claims. Sample data is fictional. Do not put production secrets in the browser or commit them to Git.

## Hackathon build notes

The prototype adapts the existing PazaLink concept into a new payment workflow. It must be materially tested with a PayPal sandbox account and Nebius Token Factory before it can be described as a verified end-to-end integration or submitted as a complete entry. The deployed demo should use environment-managed secrets and should not expose them to the client.

## License

MIT. See `LICENSE`.

## Firebase AI Logic local validation

A separate Gemini review path uses Firebase AI Logic with App Check enforced.
Use the dedicated Spark project described in `docs/FIREBASE.md`, provision AI
Logic with the Firebase CLI or MCP tool, and privately register a local App Check
debug token. Save it as `FIREBASE_APPCHECK_DEBUG_TOKEN` in the ignored `.env`.
Only an authenticated loopback client can retrieve local AI settings; responses
are not cached. Never publish debug credentials or expose this development
server through a tunnel. Production attestation is required for a hosted app.

The browser SDK is bundled and checked in for running the Python app without a
Node build step. To rebuild it: `npm ci --legacy-peer-deps`, then `npm run build:sdk`.
The selected model is `gemini-3.8-flash`, listed for the Gemini Developer API
without Blaze in the official Firebase AI Logic model catalog. A configured path
is not proof of successful inference; see the evidence report for actual results.
Nebius still requires real Nebius/NVIDIA inference for that competition.
