# Existing Firebase integration

## Dedicated demo project (24 October 2026)

Project `pazalink-demo-261024` has Google sign-in enabled and a web app registered.
Firestore database `pazalink` uses Enterprise native mode in `africa-south1`
(Johannesburg). The database reports `freeTier: true`; project billing is disabled.
Set `FIRESTORE_DATABASE_ID=pazalink` to select this named database. Existing
installations may omit it to retain `(default)`.

The existing backend-only Firestore rules compiled and deployed successfully.
They deny client SDK access; server authorization and tenant scoping remain
essential because Admin SDK calls bypass these rules. Local Application Default
Credentials were saved with user approval. A genuine Admin SDK read of the named
database and Firebase Auth user listing succeeded. Loopback `127.0.0.1` is an
authorized OAuth domain. Actual browser Google sign-in, creation and refresh of fictional invoice
`PL-F6D2E5CBCE752AA8` (USD 1.00), and sign-out clearing the invoice view
were verified. Two-identity isolation and revoked-token live checks remain pending.
No service-account key was created. `.env` remains private and ignored.

PazaLink uses Google sign-in through Firebase Authentication and server-side Firebase Admin token verification. Invoice documents are scoped under `pazalink_users/{verified_uid}/invoices`; the client does not choose its owner ID. The browser never receives service-account credentials.

Use the dedicated demo project above for fictional validation data. Do not point test runs at production customer data.

Configure the public Firebase web app identifiers on the server: `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`, and `FIREBASE_APP_ID`. Enable the intended Google sign-in provider and authorized local/hosted domains in that project. Backend credentials must use trusted Application Default Credentials or `GOOGLE_APPLICATION_CREDENTIALS` pointing to a private file outside this repository. Grant only the permissions needed for the test project. Never commit that file or expose it through static hosting.

Protected endpoints require a Firebase ID token in `Authorization: Bearer ...`; the server checks revocation. The Admin SDK accesses Firestore on the server, so browser rules do not replace these server authorization checks. The dashboard's invoice controls operate only after sign-in. The explicitly labeled local rules endpoint is independent of Firebase and does not create invoices.

Live verification still required: sign in with two controlled test identities; create a fictional invoice under each; confirm the other identity cannot list its records or access its events; test expired/revoked tokens and sign-out. Existing offline tests use dependency overrides and store doubles and do not prove deployed Firebase behavior.
