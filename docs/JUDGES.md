# Running PazaLink for judging

The demonstrated build is on branch `codex/validated-review-demo` (PR #5). Main may not contain the reviewed changes. This is a local Python web app; no public application server is claimed. The checked-in browser SDK bundle means Node is unnecessary to run it.

## Requirements

Python 3.11+, a desktop browser, a free PayPal developer account, a separate generated sandbox buyer, and your own Firebase Spark project with Google sign-in, Firestore and Firebase AI Logic enabled. Use fictional data only. Do not request or publish the author's personal Google credentials or private sandbox secrets.

1. Clone the repository and check out `codex/validated-review-demo`.
2. Create/activate a Python virtual environment; run `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and keep it private.
4. In your Firebase Spark project, register a web app and copy its API key, auth domain, app ID and project ID into the corresponding `.env` fields. These web identifiers are public configuration, not Admin credentials.
5. Enable Google sign-in. Set your own support email/brand in `firebase.json` before deploying its auth configuration. Add `127.0.0.1` to Authentication > Settings > Authorized domains.
6. Create a named Firestore database `pazalink` in native mode; set `FIRESTORE_DATABASE_ID=pazalink`. The demonstrated database is Enterprise native mode in `africa-south1` and reports its free tier enabled. Keep billing unlinked. Deploy the existing backend-only rules to your project: `npx -y firebase-tools@latest deploy --only firestore:rules --project YOUR_PROJECT_ID`. The rules deny client SDK access; the backend uses Admin SDK credentials and verified-user paths.
7. Install the official Google Cloud CLI, then run `gcloud auth application-default login` with an account authorized for your own test project. Run `gcloud auth application-default set-quota-project YOUR_PROJECT_ID`. This stores credentials locally; never upload or commit that file. See Google's [local ADC guide](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).
8. Provision Firebase AI Logic using the Gemini Developer API (the free Spark path), through the Firebase console or `npx -y firebase-tools@latest init ailogic`. Select the registered web app. Keep App Check enforced for Firebase AI Logic. In App Check > Apps > your web app > Manage debug tokens, register a private local debug token and save it as `FIREBASE_APPCHECK_DEBUG_TOKEN` in `.env`. This local demo uses `gemini-3.8-flash`; check [current supported models](https://firebase.google.com/docs/ai-logic/models) if reproducing later. Never deploy a debug token publicly. See the [official AI/App Check setup](https://firebase.google.com/docs/ai-logic/app-check).
9. In PayPal Developer > Apps & Credentials > Sandbox, obtain your sandbox application's client ID and secret. Set `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, and the official sandbox base URL from `.env.example`. Under Testing Tools > Sandbox Accounts, use a separate generated Personal buyer account. Never use a live account/card for the checkout test. Generate a private signing secret of at least 32 characters for `PAYPAL_ORDER_SIGNING_SECRET`. Opt into controlled capture with `ENABLE_SANDBOX_CAPTURE=true`.
10. Run `python -m uvicorn app:app --host 127.0.0.1 --port 8790 --env-file .env`, then open `http://127.0.0.1:8790/`.

## Demonstrated workflow

Sign in with Google. Create a fictional USD 1.00 invoice, then Refresh to read it back. Select Amani Textiles and run a real review: the untrusted sample note says bank details changed. The app displays a structured checklist and fixes the action to human review. Temporary provider failures stay visible and never become successful local-rule responses.

Select `PAZA-TEST-001` (fictional USD 1.00), create a PayPal sandbox order, and attempt capture before approval: it must be rejected. Follow the sandbox approval link and sign in with the generated sandbox buyer. Confirm the USD 1.00 amount and approve. Return to PazaLink and check approval/capture. Only matching COMPLETED processor captures are confirmed. Repeat the capture action: it reconciles the same capture ID. The sample ledger is not marked paid automatically. Sign out: invoice access clears.

Receipts expire after one hour and are bound to the signed-in Firebase UID and exact order/reference/amount. Use the same browser session for order creation and capture. An expired receipt requires a fresh controlled order; do not disable receipt validation.

## Tests and limits

`pip install -r requirements-dev.txt`, then `python -m pytest -q`. Offline tests use mocks/doubles and do not prove provider availability. Live evidence is documented separately in `REVIEW_DEMO_VALIDATION.md`. Provider quotas/high demand can cause temporary errors. Two-user/revoked-token live tests remain pending. No production settlement, bank, FX, M-Pesa, or blockchain integration is claimed.

Public deployment needs production App Check attestation and appropriately scoped server credentials. Do not expose this local debug server through a tunnel or upload personal ADC. Nebius evaluation requires a separate real Nebius/NVIDIA integration, which this Gemini build does not establish.
