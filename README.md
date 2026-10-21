# PazaLink Trade Desk

An AI-assisted payment and reconciliation workspace for East African cross-border traders. This repository is a new prototype built for the PayPal AI Hackathon and the Nebius × NVIDIA Global AI Hackathon.

## Current status

- The interface runs with clearly labeled synthetic sample transactions.
- PayPal sandbox order creation and capture are implemented server-side and require PayPal sandbox credentials.
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

Open `http://127.0.0.1:8000`. The app works in demo mode without secrets. To enable PayPal, set `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` from a PayPal **sandbox** application. To enable the required NVIDIA model path, set `NEBIUS_API_KEY`; the default model is `nvidia/nvidia-nemotron-3-nano-30b-a3b` through Nebius Token Factory.

## Safety and scope

This prototype does not initiate live payments. PayPal endpoints are hard-wired to the sandbox. AI output is decision support only: it does not execute transfers, make credit decisions, or verify geology, identity, invoices, or merchant claims. Sample data is fictional. Do not put production secrets in the browser or commit them to Git.

## Hackathon build notes

The prototype adapts the existing PazaLink concept into a new payment workflow. It must be materially tested with a PayPal sandbox account and Nebius Token Factory before it can be described as a verified end-to-end integration or submitted as a complete entry. The deployed demo should use environment-managed secrets and should not expose them to the client.

## License

MIT. See `LICENSE`.
