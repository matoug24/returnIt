# 07 — Test strategy

[Documentation index](../README.md) · Previous: [Implementation roadmap](06-implementation-roadmap.md) · Next: [Security, privacy, and operations](08-security-privacy-and-operations.md)

## 1. Quality model

Testing protects four kinds of truth:

1. **Commercial truth:** quote, payment, subscription entitlement, refund, tax, and receipt agree and reconcile.
2. **Operational truth:** capacity, route, package identity, custody, and exception ownership cannot silently diverge.
3. **Customer truth:** bilingual/accessibly presented status is derived from authoritative facts and distinguishes windows from estimates.
4. **Security/privacy truth:** only the right actor sees or changes the minimum necessary information, with auditable purpose and retention.

The team owns quality; QA does not become a downstream gatekeeper. Tests use synthetic data unless a governed production diagnostic explicitly requires otherwise.

## 2. Test pyramid and execution

| Layer | Examples | Frequency |
|---|---|---|
| Static/fast | format, type check, schema lint, translation keys/placeholders, migration graph, IaC policy, secret/dependency/container scan | Every change |
| Unit | policy calculations, state transitions, authorization decisions, ETA thresholds, serializers, redaction | Every change |
| Property/model-based | money/rounding, capacity concurrency model, custody state machine, time windows/DST, idempotency, routing invariants | Every change / nightly larger generation |
| Component/integration | FastAPI + real PostgreSQL/PostGIS, outbox/SQS, S3 upload/scan, Cognito/JWT boundary, Stripe/Google adapters | Every change for affected module; full suite main/nightly |
| Contract | OpenAPI compatibility; consumer/provider events; recorded/sandbox Stripe, Google, push contracts | Every change; sandbox scheduled |
| End-to-end | customer→dispatch→driver→handoff→proof/refund across web/mobile/admin | Main/staging and release |
| Non-functional | load/soak, resilience, security, accessibility, localization, device/network, restore/rollback | Scheduled and release gate |
| Production verification | synthetic canary and post-deploy smoke with isolated test tenant/data | Every production deployment |

Prefer narrow deterministic tests. Do not mock PostgreSQL semantics for transactions, PostGIS, locks, or constraints. Provider fault simulations remain in addition to—not instead of—sandbox smoke tests.

## 3. Traceable acceptance catalogue

| ID | Requirement coverage | Scenario and expected result | Primary levels |
|---|---|---|---|
| AC-01 | FR-001–004, NFR-006–007 | Customer checks service, switches EN/FR mid-flow, signs in, and completes keyboard/screen-reader booking without lost input | E2E, accessibility, localization |
| AC-02 | FR-010–015 | Eligible package receives server quote and one confirmed booking; invalid/expired quote or preparation failure gives actionable result | Unit, integration, E2E |
| AC-03 | FR-012, NFR-002 | Two confirmations race for one capacity unit; exactly one commits and the other receives refresh guidance; no duplicate charge | Concurrency integration, property |
| AC-04 | FR-016 | Allowed cancellation/reschedule previews fee/refund, moves/releases capacity atomically, preserves history and notifies affected route | Integration, E2E |
| AC-05 | FR-020–023 | Client retry plus duplicate/out-of-order Stripe events yields one booking/charge/entitlement/refund projection and reconciliation passes | Contract, integration, resilience |
| AC-06 | FR-030–032 | Routing corpus respects every hard constraint, balances soft preference, and reports every unassigned job/reason; publish creates immutable version | Simulation, contract, E2E |
| AC-07 | FR-033–035 | Assigned driver picks up and hands off correct package with required evidence; unassigned/stale/invalid transitions are rejected safely | Mobile E2E, integration, security |
| AC-08 | FR-033, NFR-002 | Offline commands/media survive app/process restart, sync once, and surface conflicting route/package version without overwriting truth | Physical-device, resilience |
| AC-09 | FR-036 | Partially completed route leaves each remaining stop/package assigned to an explicit outcome/owner and reconciles onboard inventory | Integration, E2E |
| AC-10 | FR-040–042 | Route start, ETA thresholds, pickup, delay, and handoff produce localized deduplicated messages; oscillation/provider failure causes no spam or fulfilment rollback | Unit/property, integration, E2E |
| AC-11 | FR-043–044 | Support opens and resolves no-show, invalid label, rejected, lost/damaged, failed handoff, and proof-dispute cases without altering original custody evidence | E2E, authorization |
| AC-12 | FR-050–052 | Effective-dated config and privileged action require correct role/reason/approval and produce redacted audit; unauthorized exports are concealed | Integration, security |
| AC-13 | NFR-005, 008–010 | Retention/privacy request, restore, DLQ replay, deployment rollback/forward migration, alarms and trace correlation work in staging | Operational exercise |

Every story links at least one `FR/NFR` and an `AC` or adds a new acceptance ID. CI test reports publish these IDs as tags. A release trace report lists requirement → code change → tests → result → accepted exception/owner.

## 4. Unit and property-based focus

### State machines

Generate valid and invalid command sequences for booking, package, route, payment projection, and cases. Invariants:

- terminal events cannot regress; corrections append rather than mutate;
- possession cannot begin without accepted pickup and cannot end twice;
- completed booking has no unowned nonterminal package;
- refund/credit does not imply operational cancellation, or vice versa;
- duplicate command IDs are semantic no-ops and altered reuse conflicts.

### Money and entitlement

Generate line items, discounts, GST/QST configuration, rounding boundaries, refunds, cancellations, and currency rejection. Assert sums in integer minor units, nonnegative constraints where required, exact quote snapshot reproduction, no over-refund, and entitlement conservation (`available + reserved + consumed`, accounting for explicit grants/expiry).

### Time and capacity

Generate windows across DST changes, leap dates, cutoffs, boundaries, preferred-time edges, hold expiry, and concurrent reservations. Assert UTC/local round trip, preferred time inside hard window, no overbooking, expired holds unusable, and reschedule atomicity.

### ETA and notifications

Generate noisy/stale GPS and ETA sequences around 15/1-minute thresholds. Assert confidence gates, one notification per semantic key, hysteresis, material-delay reset rules, quiet/fallback policy, and correct locale/template placeholders.

### Routing

For normalized provider outputs, assert every shipment is assigned or diagnosed, precedence, hard windows, breaks, capacities, start/end, destination hours, and locked-stop stability. Metamorphic tests verify that increasing capacity cannot alone make a previously feasible identical plan infeasible (allowing provider nondeterminism to change score/order, not invariants).

## 5. Integration and contract tests

- Run transactions, row locks, isolation, uniqueness, outbox claiming, PostGIS containment/distance, migration, and query plans against the supported PostgreSQL major/PostGIS version.
- Test queue visibility timeout, duplicate delivery, poison message/DLQ, retry timing, consumer crash before/after side effect, and controlled redrive.
- Verify S3 presign scope/expiry/size/content type, checksum, multipart interruption, malware quarantine, orphan cleanup, redacted retrieval, and unauthorized object denial.
- Verify JWT signature/issuer/audience/expiry, revoked/disabled user behavior, assignment and resource ownership, staff scope, step-up and service IAM boundaries.
- Diff OpenAPI and event schemas for breaking changes. Consumer contract fixtures cover additive fields, unknown enum handling policy, and version migration.
- Stripe: signed raw payload, old/new secret rotation, replay-window behavior, duplicate/out-of-order events, timeout after provider success, subscription lifecycle, dispute/refund, reconciliation.
- Google: auth/quota/timeout, invalid/infeasible requests, missing jobs, nonsensical times, large input limits, cost counter, and provider response evolution.
- Push/email: token registration/revocation, receipts/bounces, template placeholder parity, fallback and suppression.

## 6. End-to-end scenario packs

### Happy path

Book two packages under one window, one paid and one subscription-covered variant; route and publish; driver works stops, captures pickup evidence offline/online, hands packages to different destinations, and customer receives separated proof. Reconcile booking, inventory, events, notifications, payment, and audit.

### Required exception pack

Each release tests: cancellation, reschedule after draft route, customer no-show, missing/invalid label, rejected package, driver delay/window risk, failed/closed destination, partial route completion, refund and credit, lost/damaged package, notification failure, duplicate webhook, offline driver/conflict, and proof dispute. For each assert customer copy, operator owner, immutable timeline, financial independence, privacy, and route/inventory reconciliation.

### Role/adversarial pack

Customer attempts another customer's resource; driver requests old/unassigned route and broad customer list; support exceeds refund limit; dispatch changes roles; finance reads precise live location; admin tampers with evidence; webhook lacks valid signature. All fail with correct audit and without resource-existence or sensitive-data leaks.

## 7. Mobile and device matrix

Support policy must name minimum iOS/Android versions before launch. Test at least the oldest supported and current major OS on representative low-/mid-/high capability physical devices, plus emulators for breadth.

Cover fresh/upgrade install, denied/limited/revoked location/camera/photo/notification permissions, foreground/background/terminated behavior, battery saver, low storage, camera/scanner failure, orientation/font scaling/screen reader, French locale, DST/timezone change, airplane mode/flaky/slow networks, app kill/restart, token expiry, OS update, upload interruption, and device clock skew. Measure battery/network usage during a representative shift; set an approved baseline after the first instrumented build.

## 8. Performance, load, and resilience

### Performance gates

Before pilot, agree a workload model: concurrent customers/staff/drivers, bookings/hour, route size, GPS samples, evidence size, notifications, provider latency, and growth headroom. Test at expected peak and a documented burst (initial suggestion: 2× expected peak, subject to cost and realism).

Provisional engineering gates at the tested envelope:

- ordinary API reads p95 <500 ms and ordinary writes p95 <1 s, excluding declared asynchronous/provider work;
- error rate <1% excluding intentional validation and injected dependency faults;
- no lost/duplicate domain side effects; queue oldest-message age returns to steady state after burst;
- booking/custody database contention remains bounded with no capacity violation;
- route planning completes before the operational review cutoff for maximum pilot route set;
- mobile route load and offline action feedback remain usable on the minimum device.

These are launch test thresholds, not external SLAs. Record measured throughput, infrastructure size, data volume, provider behavior, and confidence; revise from evidence.

### Resilience experiments

Kill API/worker tasks mid-transaction/side effect; force RDS failover in staging; delay/duplicate/reorder SQS; block Stripe/Google/push/SES; exhaust a provider quota; expire credentials; serve stale GPS; fill a DLQ; interrupt S3 upload; deploy incompatible feature flag; and restore a backup into isolation. Assert bounded degradation, alerts, no false success, recovery/reconciliation, and customer/operations guidance.

## 9. Security and privacy validation

- Threat model at foundation, booking/payment, driver location/evidence, and pre-launch; track mitigations.
- SAST, dependency/license, secret, container, IaC and API DAST in CI/schedule; critical/high findings follow an approved remediation/risk-acceptance policy.
- Independent penetration test before broader public launch and after material auth/payment/evidence boundary changes.
- Verify data inventory, access logs, consent versions, retention/deletion jobs, legal holds, data export/correction, backup expiry, and third-party deletion limitations.
- Inspect logs/traces/analytics/crash reports for tokens, full addresses, barcodes, photos, card data, and unnecessary location.

## 10. Accessibility and localization

- Automated axe-equivalent checks and linting are necessary but insufficient. Manual keyboard, focus order, screen-reader, landmarks/headings, errors, contrast, zoom/reflow, reduced motion, target size, and timeout tests cover each critical web path.
- Native tests cover VoiceOver/TalkBack, dynamic type, labels/hints/roles, focus after errors/navigation, contrast, motion, touch targets, camera alternatives, and permission explanation.
- Pseudo-localization detects truncation/hard-coded strings. Automated checks enforce key/placeholder/plural parity; bilingual reviewers approve critical copy. Test French accents, longer strings, Canada currency/date/address/phone formats, mixed-language provider content, and notification deep links.
- Target WCAG 2.2 AA for web, with documented exceptions/remediation and qualified accessibility review; this document does not decide legal applicability.

## 11. Test data and environments

- Factories generate valid/invalid synthetic Montreal-like addresses and coordinates that do not identify real residents. Named deterministic personas cover each role/locale and are resettable.
- Provider fixtures contain no production secrets/personal data and are checked against current schemas. Contract tests redact recorded responses consistent with licensing.
- Staging has production-like topology/configuration categories but separate accounts, keys, Cognito, Stripe test mode, buckets, domains, and push apps.
- Production debugging uses IDs and controlled queries. Copying production data to lower environments is prohibited by default; any exception needs documented purpose, minimization, approval, encryption, access, and deletion.

## 12. Release and production gates

Release candidate requires green required CI, migration rehearsal, no unaccepted launch-blocking defects/findings, current trace report, device/accessibility/localization evidence, provider sandbox smoke, routing corpus, reconciliation, restore/rollback exercise, runbook/alert changes, and product/ops acceptance.

Post-deploy smoke uses isolated production test identities and clearly marked non-customer work: public health, authentication, serviceability, a reversible zero/low-impact provider test where supported, queue/outbox flow, evidence presign/quarantine, admin read, and telemetry. Never create a real driver dispatch or charge without an explicit controlled procedure.

## 13. Defect severity and evidence

- **S0 launch stop:** custody/financial corruption, cross-tenant disclosure, auth bypass, restricted-goods safety failure, unrecoverable loss, or inability to rollback/stop bookings.
- **S1 critical:** critical flow unavailable/no safe workaround, systematic hard-window/route violation, missing required evidence, material accessibility/language block.
- **S2 major:** degraded flow with safe documented workaround or limited incorrect customer/operations behavior.
- **S3 minor:** cosmetic/noncritical issue.

Retain test artifacts according to policy: result summaries, versions/configuration, logs/traces (redacted), screenshots/accessibility reports, performance models, security reports under restricted access, migration/restore records, and accountable waivers with expiry.

