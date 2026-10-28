# 08 — Security, privacy, and operations

[Documentation index](../README.md) · Previous: [Test strategy](07-test-strategy.md) · Next: [Decisions, assumptions, and open questions](09-decisions-assumptions-and-open-questions.md)

## 1. Scope and caution

This is a product-engineering control baseline, not legal, accounting, insurance, employment, or accessibility advice. Qualified Canadian/Quebec professionals must validate obligations and final policies, including Quebec's private-sector privacy regime and Law 25 changes, Canadian anti-spam rules, French-language requirements, consumer protection, taxes, employment/contractor monitoring, accessibility, and sector-specific shipping restrictions.

Returnet should designate an accountable privacy lead, document governance, and perform a privacy impact assessment before collecting continuous/precise driver location or materially changing cross-border processing. Record which legal basis/consent applies to each purpose rather than treating a privacy policy click as blanket permission.

## 2. Data inventory and classification

| Class | Examples | Baseline handling |
|---|---|---|
| Restricted | auth/session secrets, provider secrets, precise driver location history, evidence photos/receipts, access/buzzer notes, dispute/claim material | Need-to-know roles, encryption, short purpose-based retention, access logging, no analytics/log bodies |
| Confidential personal | name, contact, pickup address, booking/package history, device token, coarse location, consent | Scoped application access, encryption, masking, retention schedule, controlled exports |
| Confidential business | routes, prices, capacity, operational metrics, audit/security findings | Staff role/scope, encryption, controlled sharing |
| Public | marketing pages, public service descriptions | Integrity controls and approved publishing |

Maintain a living record of data element, purpose, source, system/region, users/recipients, subprocessors, legal basis/consent, retention/deletion, backup treatment, and owner. New collection requires review before schema/event/analytics changes.

## 3. Privacy by design

### Minimization and purpose limitation

- Ask for package contents only through eligibility categories/attestations unless an exception requires more; do not photograph people, home interiors, or unrelated labels.
- Separate access instructions from the broadly visible address and expire them after operational need.
- Give customers ETA/status, not continuous precise driver location. Give finance/support only location necessary for a case.
- Sample driver location at the lowest cadence/precision that safely supports dispatch and ETA; stop at shift/route end.
- Avoid third-party behavioral analytics in authenticated, driver, evidence, and admin surfaces until purpose/consent/data flows are approved.

### Consent and transparency

- Provide concise just-in-time English/French explanations for driver location, camera/photos, push, and optional marketing.
- Driver location notice states purpose, collection periods, visibility, retention, consequences of denial, and contact/process for questions. Consent must be meaningful where consent is the valid basis; employment power imbalance requires legal review and possibly a different basis/process.
- Store versioned consent/notice receipts. Withdrawal stops optional future processing but may not erase records lawfully required for custody, financial, security, or claims purposes.
- App Store/Play disclosures and OS permission strings must match actual SDK/network behavior.

### Individual rights and privacy incidents

- Authenticated intake supports access/correction and deletion/withdrawal requests; verify identity proportionately, track deadlines, search systems/vendors/backups, redact third-party data, and document exceptions.
- Privacy incidents are triaged for containment, evidence preservation, risk assessment, notification/recording duties, affected individuals/regulators, and prevention. Legal/privacy lead determines statutory obligations and timing.

## 4. Retention and deletion

No “keep everything” default. The privacy/legal/finance/operations review must approve exact periods. Engineering implements configurable retention classes, for example:

| Data | Draft approach to validate |
|---|---|
| Live driver samples | Short operational window; derive route events/aggregates then delete detailed samples unless an active case/legal hold |
| Access notes | Remove/anonymize promptly after fulfilment/support window unless customer explicitly saves them for repeat service |
| Evidence/custody | Retain for claims/limitation/insurance need, then delete or anonymize; exact term pending advice |
| Financial/tax records | Retain for required accounting/tax term; minimize linkage when possible |
| Audit/security logs | Tiered hot/archive period based on threat/claims need; redact personal content |
| Notification/provider payloads | Keep delivery metadata only as long as support/consent evidence requires; avoid full content |
| Backups | Bounded lifecycle; deleted data ages out and is not restored into active use without rerunning deletion controls |

Deletion jobs are idempotent, observable, sampled/audited, and pause for scoped legal holds. Report expired-record counts and failures without exposing the records.

## 5. Security architecture and controls

### Identity and least privilege

- Cognito manages authentication; require verified channel, rate limits, breached-password protections where available, secure account recovery, and MFA for staff. Evaluate phishing-resistant MFA for privileged staff.
- Server performs object/action/assignment/scope checks. Staff roles separate dispatch, support, finance, security/privacy, and user administration; high-risk refunds/exports/role changes may require dual approval.
- ECS task roles, CI OIDC roles, and queue/bucket/key policies grant only required actions. Humans use federated short-lived access; no shared production accounts.
- Quarterly and departure-triggered access review; emergency access is time-bound, approved, alerted, and retrospectively reviewed.

### Application and API

- TLS, secure headers/cookies, CSRF protection where cookie auth is used, strict CORS, input/response schemas, parameterized SQL/ORM, output encoding, upload validation, SSRF/redirect defenses, and per-principal/IP/action throttles.
- Tokens live in platform-secure storage; web avoids long-lived tokens in browser storage. Mobile device data uses OS-protected encrypted storage and expires.
- Idempotency and optimistic/row locking protect critical commands. Audit privileged reads as well as writes where evidence/location is involved.
- WAF is a layer, not the authorization model. Protect webhook endpoints with provider signatures, replay windows and rate controls.

### Encryption and secrets

- AWS-managed encryption at rest with customer-managed KMS keys where access separation/audit warrants it; TLS to databases/providers.
- Secrets Manager for provider/database secrets, rotation where supported, strict task-role retrieval, and no secrets in images, Git, logs, crash data, URLs, or client bundles.
- Separate keys/secrets/accounts by environment. Define rotation and compromise playbooks; Stripe webhook secret overlap supports safe rotation.

### Evidence and software supply chain

- Quarantine uploads, enforce type/size/checksum, scan, strip unsafe metadata as appropriate, prevent public ACLs, and use short authorized presigned access.
- Dependency pinning/updates, SBOM, license review, signed/scanned images, protected CI, reviewed IaC/migrations, branch protection, and artifact promotion by digest.
- Inventory Expo/React Native/native SDKs and web tags; remove unused packages and verify privacy manifests/behaviors.

## 6. Quebec/Canadian product-engineering checklist

- **Privacy:** accountability/contact, privacy impact assessments where appropriate, clear bilingual notices, valid consent/legal basis, minimization, cross-border/vendor assessment, rights workflow, incident register/notification analysis, retention/destruction, and privacy settings at the most protective practical defaults.
- **Driver monitoring:** necessity/proportionality, transparent active-state indicator, no off-shift collection, worker/contractor context, access limits, dispute/correction process, and legal/employment review.
- **Language:** French experience and contracts/terms/communications must be reviewed for applicable Charter of the French Language obligations; English availability and customer choice should follow counsel, not improvised consent patterns.
- **Accessibility:** target WCAG 2.2 AA and native equivalents, document testing/remediation, publish support/contact method; determine statutory scope with counsel.
- **Taxes/receipts:** accounting determines GST/QST registration, place-of-supply, inclusive/exclusive display, subscription/refund/credit tax treatment, invoice fields, and retention.
- **Terms/consumer protection:** clearly disclose price, window versus preference/ETA, cancellation/refund, subscription renewal/cancellation, limitations, retailer-refund separation, claims, and contact; validate online-contract presentation/records.
- **Insurance/liability:** commercial auto, cargo/inland marine, general liability, cyber/privacy, workers/contractors, custody limits/exclusions, and claims process must match actual operations and contracts.
- **Restricted goods:** prohibited/regulated goods, dangerous goods, alcohol/cannabis, medicines, batteries, perishables, weapons, high-value items, personal data on devices, oversized/damaged packages, and age/identity restrictions need a reviewed list, customer attestation, driver training, refusal, and incident procedure.
- **Communications:** distinguish transactional service messages from marketing; consent/unsubscribe/sender identification and retention must meet applicable anti-spam/privacy rules.

## 7. Observability

### Correlation and telemetry

Every request/command/event has `request_id`, trace ID, correlation/causation IDs, aggregate ID/version, environment/service/release. Structured logs use allow-listed fields and redaction; addresses, precise coordinates, tokens, access notes, barcode values, photo URLs, and provider payloads are excluded by default.

Dashboards cover:

- API traffic/latency/errors/saturation by safe dimension;
- ECS health/deployments, RDS connections/locks/storage/replication/failover, SQS age/depth/DLQ, outbox lag;
- booking/capacity/payment/webhook/reconciliation health;
- routing duration/provider failures/quota/cost/infeasible/unassigned work and route risk;
- active routes/stale driver sync/evidence pending or quarantine failures/custody exceptions;
- notification queue/provider acceptance/receipts/bounce/token invalidation;
- security auth failures/rate/WAF/anomalous privileged access and retention-job failures.

Avoid high-cardinality customer/package IDs in metric labels; use traces/log search under authorized access.

### Alert principles

Page only for actionable, customer/custody/security-impacting conditions: elevated critical-path errors, oldest queue/outbox age, database exhaustion/failover, bookings accepted without valid payment/capacity, unreconciled onboard packages, provider outage near planning deadline, evidence unavailable, security signal, or backups failing. Ticket nonurgent trends. Each alert links to owner, severity, dashboard and runbook; test alerts quarterly.

## 8. Operational runbooks

Before pilot, executable runbooks cover:

1. Stop/pause new bookings or a zone/window safely.
2. Google outage/quota or infeasible planning; manual route review and no silent omissions.
3. Stripe outage/webhook backlog/reconciliation mismatch; keep state pending and avoid duplicate charges/refunds.
4. Push/SES outage; queued retry, critical fallback decision, customer/support banner.
5. Driver offline/lost device/stale route/location; revoke session, preserve custody, dispatch safe continuation.
6. Missing/damaged/rejected package and failed destination/overnight secure storage with inventory reconciliation.
7. S3 evidence quarantine/scan/access failure; do not falsely complete required proof.
8. RDS failover/restore, queue DLQ redrive, compromised secret/key rotation, rollback/feature disable.
9. Privacy/security incident and individual-right request.
10. Weather/emergency/service suspension and bilingual bulk-but-individualized reschedule process.

Runbooks state trigger, customer impact, safety first action, roles/communications, commands/UI steps with approval boundaries, validation, escalation, recovery, reconciliation, evidence retention, and post-incident tasks. They must not depend on one employee's memory.

## 9. Incident management

- Severity definitions align with [test defects](07-test-strategy.md#13-defect-severity-and-evidence). Assign incident commander, operations/customer communications, technical lead, and scribe; engage privacy/legal/insurance as facts require.
- Protect people and physical custody first, then contain digital/financial impact. Preserve immutable evidence and access logs without excessive collection.
- Use bilingual customer communications that distinguish known facts, estimates, actions, and next update. Do not speculate about breach/liability.
- Post-incident review is blameless but accountable: timeline, contributing controls, customer/privacy/financial impact, detection/recovery measures, corrective owners/dates, test/runbook changes.

## 10. Continuity and recovery

- Maintain contacts and fallback procedures for AWS, Google, Stripe, Expo/FCM/APNs, SES, carrier/retailer destinations, drivers, insurer, privacy/legal counsel, and customer support.
- Define business impact tiers and approved RPO/RTO; test RDS point-in-time restore into isolation, S3/version recovery, IaC rebuild, secrets rotation, and application compatibility.
- Reconciliation after recovery compares bookings/capacity, payments/webhooks, outbox/queues, package custody, route assignments/onboard inventory, evidence, and notifications before normal operation resumes.
- Secure physical overnight custody, manifests, access logs, and contingency destinations are part of disaster recovery, not merely software concerns.

## 11. Production readiness review

The accountable group reviews architecture/threat model, data flows/vendors, open risks, provider quotas, security scan/pentest results, privacy/accessibility/language/legal/accounting/insurance approvals, dashboards/alerts/on-call, runbooks/training, performance envelope, backup restore, deploy/rollback, store approvals, reconciliation, and stop-booking controls. Every exception has owner, expiry, compensating control, and explicit risk acceptance.

