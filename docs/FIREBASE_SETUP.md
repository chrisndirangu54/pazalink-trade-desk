# Firebase configuration for PazaLink

The operations API now uses **Firebase Authentication ID tokens** and **Cloud Firestore** instead of static bearer tokens and SQLite.

## Firebase project
1. Create/select a Firebase project, enable **Authentication** (e.g. email/password or Google) and create a **Firestore** database.
2. Set FIREBASE_PROJECT_ID on the FastAPI backend. In a trusted backend runtime use Application Default Credentials, or set GOOGLE_APPLICATION_CREDENTIALS to the path of a private service-account JSON file **outside** the git repository.
3. Obtain a short-lived Firebase ID token from the authenticated Firebase client SDK (`await user.getIdToken()`), then send `Authorization: Bearer <idToken>` to `/api/ops/...`. No static demo tokens are accepted.
4. Users' fictional invoices are stored under `pazalink_users/{uid}/invoices/{invoiceId}`; events are subcollections. The backend verifies Firebase tokens (including revocation) on each request and scopes operations to the verified UID.
5. **Backend deployments** should use a service identity with minimum required Firestore permissions. Firebase Admin SDK bypasses Firestore security rules; keep all server endpoints authenticated.

## Firestore client rules
This app uses backend-only access to invoice data. Direct client reads/writes to `pazalink_users` are denied by the supplied Firestore rules. Configure other collections separately if needed. Do not publicly expose the Admin service account.

## Payments remain sandbox only
The existing PayPal demo endpoints must not be exposed publicly without adding Firebase authorization and order ownership checks. PayPal order capture is off by default and must only be enabled in a private sandbox test environment. Production financial transactions, webhooks, signed event verification and provider settlement are not implemented.

## Verification
Run `pip install -r requirements-dev.txt && python -m pytest -q`.
The unit tests mock Firebase verification so they run without internet or a Firebase project. **A passing CI run does not prove live Firestore integration**; run separate Emulator Suite tests and a controlled staging smoke test before deployment.

## Migration
SQLite demo entries are not automatically imported. No legacy tokens are accepted. To migrate fictional records, use an audited one-time import that explicitly maps former owners to real Firebase UIDs. Never silently map arbitrary demo usernames to live accounts.
