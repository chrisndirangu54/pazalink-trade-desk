# PazaLink Trade Desk

An AI-assisted payment and reconciliation workspace for East African cross-border traders. This repository is a new prototype built for the PayPal AI Hackathon and the Nebius × NVIDIA Global AI Hackathon.

## Current status

- The interface runs with clearly labeled synthetic sample transactions.
- PayPal sandbox order creation is implemented server-side and requires sandbox credentials and Firebase sign-in. **Capture remains disabled/unimplemented** pending ownership and buyer-approval checks; do not describe an order as paid.
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
