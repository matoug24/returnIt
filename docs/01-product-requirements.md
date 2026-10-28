# 01 — Product requirements

[Documentation index](../README.md) · Next: [User flows and rules](02-user-flows-and-rules.md)

## 1. Purpose and outcomes

Returnet removes the travel and coordination burden from online returns. It must let a customer schedule a predictable home pickup, let a driver execute an efficient and auditable route, and let operations intervene before a problem becomes a lost package or missed return deadline.

The first launch is a deliberately supervised Montreal operation. Automation proposes routes and communicates progress, while dispatch retains the ability to reassign work, correct destination information, and resolve exceptions.

### Success outcomes

| ID | Outcome | Initial measure (baseline/target to validate in pilot) |
|---|---|---|
| PR-01 | Customers can complete a valid booking without staff help | Funnel completion and support-contact rate, segmented by language/device |
| PR-02 | Eligible pickups occur inside the confirmed hard window | Percentage inside window; target set after instrumented pilot |
| PR-03 | Every accepted package has defensible custody evidence | 100% of state transitions have actor/time; required pickup and handoff evidence present |
| PR-04 | Dispatch can detect and recover from route risk | At-risk stops visible before breach; exception actions fully audited |
| PR-05 | Customers understand status without interpreting logistics jargon | Notification delivery/engagement and support inquiries by status |
| PR-06 | Unit economics can be measured | Revenue, discounts/refunds, route time/distance, service time, and failed-attempt cost attributable |

Metrics are operational instruments, not public guarantees. Numerical service-level targets should be established only after a representative pilot.

## 2. Users and jobs

### Customer

Needs to verify service availability, understand preparation rules and price, book and pay, receive a bounded pickup window, track progress, present the correct package, receive evidence of pickup and destination handoff, and obtain help for exceptions.

### Driver

Needs a safe, ordered route; clear stop constraints; navigation handoff; minimal-tap status controls; barcode/QR and photo capture; offline continuity; destination instructions; and an explicit way to report no-show, unsafe conditions, invalid labels, rejection, damage, or delay.

### Dispatcher / operations agent

Needs capacity views, route proposals, manual overrides, live risk signals, driver/stop details, evidence review, customer contact actions, exception queues, and end-of-day reconciliation.

### Support, finance, and administrator

Support needs a customer timeline and policy-guided remedies. Finance needs Stripe reconciliation, taxes/receipts, credits/refunds, and subscription state. Administrators need role assignment, service configuration, reason codes, feature flags, and audit export with separation of duties.

## 3. Scope

### MVP (launch candidate)

- Montreal service zone represented by versioned polygons/postal-code rules.
- English and French web/mobile UI and transactional templates from the first release.
- Email/password or passwordless customer authentication through Cognito; verified email required, phone optional unless SMS is enabled.
- Address search, geocoding, serviceability, normalized access notes, and apartment/buzzer instructions.
- One or more independently labelled packages in a booking, each with retailer/carrier/destination details and preparation attestation.
- Next-day/within-24-hour configurable pickup windows based on capacity; a preferred time inside the window is a soft optimization goal.
- One-time card payment and one simple monthly subscription entitlement through Stripe.
- Booking confirmation, reminder, route started/window active, approximately 15-minute ETA, approximately 1-minute ETA, pickup, delay/exception, and destination-handoff notifications.
- Dispatch review of auto-generated route proposals; assignment, publish, reassignment, and exception handling.
- Driver route list/map, navigation deep link, scans, photos, timestamps, geolocation (with consent), signature/attestation when policy requires, offline queue, and sync conflict handling.
- Destination handoff with scan/photo and carrier receipt or tracking/reference number where obtainable.
- Customer/support timeline and evidence access appropriate to role.
- Refund/credit operation, audit trail, privacy requests, monitoring, backups, and incident-ready runbooks.

### Later phases

- Dynamic same-day/on-demand pickup and continuous reoptimization.
- Dedicated driver app/codebase if release cadence or permissions justify it.
- Multi-depot, multi-city, marketplace/gig-driver onboarding, driver earnings, and contractor tax workflows.
- Retailer/carrier API integrations, label generation, locker support, and automated receipt parsing.
- Advanced subscription tiers, family/business accounts, bundles, credits, promotions, and invoicing.
- Vendor-independent optimization using Amazon Location data plus OR-Tools, or a managed solver selected by benchmark.
- Predictive service time, demand forecasting, automated capacity pricing, and customer self-service claims.

### Explicitly out of MVP

- Accepting unapproved returns or deciding whether a retailer will refund the customer.
- Packaging services, label printing by default, hazardous/restricted goods, oversized freight, cash, or unattended entry into a residence.
- Guaranteeing exact pickup times, retailer refunds, carrier scan timing, or delivery by the retailer's return deadline.

## 4. Functional requirements

### Discovery, account, and localization

- **FR-001:** A visitor can check serviceability and indicative availability without creating an account.
- **FR-002:** Sign-up/login, consent notices, policies, support content, errors, receipts, and notifications are available in English and French; the user can change language without losing work.
- **FR-003:** The platform stores language, timezone, notification preferences, and versioned consent receipts independently.
- **FR-004:** Accessible keyboard/screen-reader flows exist for public/customer/admin web; mobile follows native accessibility semantics and dynamic text sizing.

### Booking and pricing

- **FR-010:** The customer enters a validated pickup address, package count/attributes, return method, destination/label data, and access instructions.
- **FR-011:** The platform rejects or routes for review packages outside configured size, weight, content, service-area, return-deadline, or destination rules.
- **FR-012:** Capacity service returns only bookable hard windows. A preferred time, when accepted, must fall inside the selected window and is labelled non-guaranteed.
- **FR-013:** A server-calculated, expiring quote itemizes base pickup, package/add-on charges, discounts, taxes, subscription entitlement, and total in CAD.
- **FR-014:** The customer accepts preparation/restricted-goods attestations and applicable terms before payment/confirmation.
- **FR-015:** Booking confirmation is idempotent: retries cannot create duplicate bookings or charges.
- **FR-016:** The customer can cancel or reschedule within policy; the UI shows any fee/refund before confirmation.

### Payments and subscriptions

- **FR-020:** Stripe is the payment processor and subscription billing system; Returnet stores provider identifiers and a local accounting projection, never raw card data.
- **FR-021:** Webhooks are signature-verified, persisted, deduplicated, and processed asynchronously. Out-of-order events converge to provider state.
- **FR-022:** Booking state is not inferred from a client redirect. Fulfilment requires server-verified payment or a valid subscription entitlement.
- **FR-023:** Refunds, credits, charge disputes, subscription renewal/failure/cancellation, tax amounts, and receipt references are auditable.

### Dispatch, routing, and driver execution

- **FR-030:** Route generation respects hard pickup windows, shift/break/capacity constraints, service times, route start/end, destination hours, and package compatibility; it treats preferred times as weighted soft goals.
- **FR-031:** Dispatch sees unassigned, infeasible, at-risk, active, and exception work and can override suggestions with a required reason.
- **FR-032:** Publishing a route creates a versioned, immutable plan snapshot and notifies the assigned driver; later changes create a new version.
- **FR-033:** Driver actions are authenticated, authorized to assignment, timestamped on device and server, and safely retryable offline.
- **FR-034:** Pickup requires configured evidence, normally a matching package/booking scan plus photo; discrepancies require a reason and dispatch resolution.
- **FR-035:** Final handoff requires destination evidence appropriate to the method: scan, receipt/reference, photo, timestamp, and location where permitted/available.
- **FR-036:** Partial route completion is valid; every remaining stop must be explicitly carried over, reassigned, cancelled, or exceptioned.

### Tracking, communication, support

- **FR-040:** Customer status is derived from authoritative booking/package events and avoids exposing driver-sensitive details.
- **FR-041:** ETA notifications are estimate bands with throttling/hysteresis; they never change the confirmed hard window or promise an exact arrival.
- **FR-042:** Notification attempts have template/language/version, channel, provider outcome, and retry/dead-letter state. A push failure cannot block fulfilment.
- **FR-043:** Support can view a chronological case timeline, add internal notes, contact the customer, request evidence review, issue policy-limited remedies, and escalate claims.
- **FR-044:** Customers can report missing/damaged packages or dispute proof without altering the original audit record.

### Administration

- **FR-050:** Authorized staff can configure service zones, operating calendars, windows/capacity, package limits, prices/tax settings, reason codes, destination hours, and feature flags with effective dates and audit history.
- **FR-051:** Role-based permissions separate dispatch, support, finance, and administration; privileged actions require step-up authentication where supported and an audit reason.
- **FR-052:** Operations can export reconciliation and audit data subject to least privilege, purpose, and retention controls.

## 5. Non-functional requirements

- **NFR-001 Availability:** Design for multi-AZ production dependencies and graceful degradation. Set formal SLOs after pilot traffic and support coverage are known.
- **NFR-002 Integrity:** No acknowledged state-changing request may be silently lost. Financial, custody, and audit writes use transactions, idempotency, and immutable event history.
- **NFR-003 Performance:** At MVP launch gate, demonstrate p95 under 500 ms for ordinary cached/read API requests and under 1 s for ordinary writes, excluding third-party work, at the agreed tested load. Booking/routing third-party operations are asynchronous or expose progress when longer.
- **NFR-004 Scale:** Stateless services scale horizontally. Capacity assumptions and tested envelopes are recorded per release; no unsupported peak claim is advertised.
- **NFR-005 Privacy/security:** Encrypt in transit/at rest, minimize collection, segregate privileged access, record consent, and support access/correction/deletion workflows subject to legal retention.
- **NFR-006 Accessibility:** Target WCAG 2.2 AA for web experiences and equivalent native accessibility practices; verify with automated and manual testing.
- **NFR-007 Localization:** No user-visible string is hard-coded; locale-aware date/time/currency/address formats and bilingual templates are release gates.
- **NFR-008 Observability:** Correlated logs, metrics, traces, business events, provider delivery state, and alertable queues exist without logging secrets or unnecessary personal data.
- **NFR-009 Recoverability:** Automated encrypted backups and point-in-time recovery are enabled; recovery objectives are selected and exercised before launch.
- **NFR-010 Maintainability:** Typed contracts, migration discipline, automated tests, feature flags, infrastructure as code, and documented rollback are required.

## 6. Release-level acceptance criteria

The MVP may enter a controlled Montreal pilot when all of the following hold:

1. A bilingual customer can create, pay for, reschedule/cancel, and track a booking on supported web, iOS, and Android builds, including accessible critical paths.
2. Capacity never intentionally offers a window that violates configured service area/calendar/capacity rules; concurrent last-slot booking is handled atomically.
3. A dispatcher can generate, inspect, publish, revise, and reconcile a route; infeasible jobs are explained rather than silently omitted.
4. A driver can complete the full pickup-to-handoff flow and every required custody transition has actor, server time, source, package identity, and configured evidence.
5. Offline driver actions survive process restart and synchronize without duplicating transitions; conflicts surface to the driver/dispatch.
6. Payment and webhook retries do not create duplicate charges, entitlements, refunds, bookings, or notifications.
7. The listed exceptions in [user flows](02-user-flows-and-rules.md) have an operator-visible state, owner, safe customer message, and tested recovery.
8. Backup restore, rollback, queue replay/dead-letter handling, key alarms, and a third-party outage exercise have been completed in staging.
9. Security/privacy review, threat model, retention configuration, driver-location consent, bilingual terms/privacy content, insurance/liability policy, restricted-goods policy, and tax/receipt treatment have named accountable approvals. This is a launch gate, not a claim that this draft provides legal advice.
10. Each requirement has passing traceable tests or a documented, accepted exception; production smoke checks pass after deployment.

## 7. Product analytics (privacy-minimized)

Measure funnel steps, window availability, preferred-time deviation, on-time pickup, service duration, route distance/time, failed attempts, handoff latency, notification outcomes, refund/claim rate, subscription use, and support contacts. Use stable internal IDs rather than raw addresses in analytics; restrict detailed location data to operational systems and short, justified retention. Define event names and consent/cookie treatment before enabling third-party analytics.

## 8. Product risks

- Return instructions differ by retailer and can change after booking; require customer attestation and dispatch review paths.
- Route optimization can produce mathematically valid but operationally unsafe plans; retain human review and collect driver feedback.
- Carrier opening hours, traffic, weather, construction, and apartment access can invalidate estimates.
- Chain-of-custody evidence reduces disputes but does not transfer all liability; policy and insurance must match real operations.
- Bilingual and accessible experiences require continuous testing, not launch-only translation/audits.
- Subscription abuse or unprofitable usage requires transparent limits that are not yet decided.

