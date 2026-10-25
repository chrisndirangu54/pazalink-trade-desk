# PazaLink validation and submission evidence

25 October 2026 (Africa/Nairobi).

## Verified live workflows

- Firebase Google sign-in; server verifies ID tokens with revocation checks.
- Fictional Firestore invoices created and refreshed through the actual authenticated browser UI. Sign-out clears the protected view. An unauthenticated invoice-list request returns HTTP 401.
- Firebase AI Logic with enforced App Check and private local debug token. Complete structured Gemini 3.8 Flash reviews flagged unverified beneficiary changes for fictional invoice PL-2048. The app fixes the action to human review and cannot authorize payment.
- PayPal sandbox: authenticated browser order 74N421906U918074A for fictional USD 1.00, rejected capture before approval, separate generated sandbox buyer approval, COMPLETED capture 798282074M801545V, and repeated capture reconciliation to the same ID.
- Earlier direct adapter order 5XL09715K7475635L/capture 4J214726CW1053453 is separate evidence and not the authenticated UI walkthrough.

## Automated validation

55 offline tests pass with one Starlette TestClient deprecation warning. Tests cover model output validation, payment receipt ownership/tampering/expiry, provider amount/reference/currency/status checks, idempotency and reconciliation, plus auth/loopback/origin protection and no-cache handling for private Firebase AI settings. JavaScript syntax checks pass. GitHub Actions passed implementation commit f3fe8d7b624142777ff00c99b692fc45b06a93d7.

## Recording

An actual captioned screen walkthrough is provided in the evidence package, under three minutes. Browser screenshots were sampled during real actions. Each segment retains its observed timing; hard cuts remove sign-in and model waits. Intro/invoice/AI/result/sign-out retakes improve privacy and readability. No simulated screens, real customer data or production payments appear. Account identity is hidden in the app UI. The video is silent with a technical caption narrative.

## Limitations and remaining submission steps

- A later Gemini request returned HTTP 500 high demand; failure remained visible. Earlier SDK registration errors/timeouts were fixed or reported, never counted as successes. The small connectivity probe hit MAX_TOKENS and is labeled incomplete.
- Live two-user isolation and revoked-token exercises remain pending; offline tests are not a substitute for those checks.
- Dedicated project pazalink-demo-261024 uses Spark, billing disabled, named Enterprise native database pazalink in Johannesburg with freeTier=true. No service-account key or paid service was created.
- This is a local runnable demo. No public hosted application URL exists. Production hosting needs production App Check attestation and scoped server credentials; never expose local debug settings or personal ADC through a tunnel.
- Public YouTube publication and final Devpost submission status must be verified separately. A local MP4 is not a public YouTube link.
- Nebius/NVIDIA inference remains unverified; this Gemini demonstration cannot satisfy that competition.
- PR #5 remains unmerged for review. No application submission or production merge is claimed.

Official PayPal rules: https://paypalaihackathon.devpost.com/rules . Deadline 12 November 2026, 12:00 PST (23:00 Nairobi); public licensed source, meaningful PayPal sandbox and AI functionality, public YouTube video under three minutes, and runnable/demo access instructions. Recheck the form before final submission.
