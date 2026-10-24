# Existing Firebase integration

PazaLink uses Google sign-in through Firebase Authentication and server-side Firebase Admin token verification. Invoice documents are scoped under `pazalink_users/{verified_uid}/invoices`; the client does not choose its owner ID. The browser never receives service-account credentials.

Use the intended existing Firebase project. No Firebase project or database was provisioned during this validation. Before connecting a database, confirm its ID, location, edition, billing status and access policy in the Firebase console. Do not point test runs at production customer data.

Configure the public Firebase web app identifiers on the server: `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`, and `FIREBASE_APP_ID`. Enable the intended Google sign-in provider and authorized local/hosted domains in that project. Backend credentials must use trusted Application Default Credentials or `GOOGLE_APPLICATION_CREDENTIALS` pointing to a private file outside this repository. Grant only the permissions needed for the test project. Never commit that file or expose it through static hosting.

Protected endpoints require a Firebase ID token in `Authorization: Bearer ...`; the server checks revocation. The Admin SDK accesses Firestore on the server, so browser rules do not replace these server authorization checks. The dashboard's invoice controls operate only after sign-in. The explicitly labeled local rules endpoint is independent of Firebase and does not create invoices.

Live verification still required: sign in with two controlled test identities; create a fictional invoice under each; confirm the other identity cannot list its records or access its events; test expired/revoked tokens and sign-out. Existing offline tests use dependency overrides and store doubles and do not prove deployed Firebase behavior.
