# 09 — Decisions, assumptions, and open questions

[Documentation index](../README.md) · Previous: [Security, privacy, and operations](08-security-privacy-and-operations.md) · [Glossary](glossary.md)

## 1. How to maintain this register

- **Decision** means the draft selects a direction; change it deliberately and record rationale/impact.
- **Assumption/default** makes the draft coherent but requires validation. It is not an accidental requirement.
- **Open question** needs an owner and target milestone. Only questions marked launch-blocking should stop launch.
- Consequential accepted architecture changes should be promoted to an ADR with status, context, options, decision, consequences, security/privacy impact, and rollback/migration path.

## 2. Accepted draft decisions

| ID | Decision | Rationale and consequences | Revisit trigger |
|---|---|---|---|
| D-001 | Product name is **Returnet**; folder may remain WeReturnIt temporarily | Consistent customer/project terminology; rename code/repository when implementation begins if desired | Trademark/name/legal review or owner change |
| D-002 | Launch is one Montreal service area, bilingual EN/FR | Contains operational variability while meeting product direction | Proven pilot and expansion readiness |
| D-003 | Confirmed window is hard; preferred time is soft and non-guaranteed | Preserves service promise while allowing efficient routing | New priced exact-time product |
| D-004 | Modular FastAPI monolith plus independent workers | Strong transactional core and lower operational overhead with extraction seams | Scaling/team/security boundary evidence |
| D-005 | PostgreSQL/PostGIS via RDS is source of transactional/geospatial truth | Transactions and spatial support; demands migration/connection discipline | Measured engine/scale limitation |
| D-006 | ECS Fargate is default compute | One container operating model for API, Next.js SSR and workers | Cost/latency profile clearly favors another service |
| D-007 | SQS handles work; EventBridge handles schedules/integration fan-out; transactional outbox connects commits | Explicit durability/backpressure and no dual-write fiction | Proven event platform requirements |
| D-008 | Cognito authenticates; application enforces domain roles/assignments | Managed identity without coupling authorization to token claims | Federation/UX/security shortcomings |
| D-009 | Google Route Optimization is primary MVP solver behind an abstraction | Fits hard/soft time windows and vehicle constraints; adds vendor/data/cost dependency | Benchmark, cost, licensing, reliability or independence requirement |
| D-010 | Amazon Location + OR-Tools is the documented later alternative, not MVP dual-build | Avoids building/tuning two solvers; enables evidence-based migration | Vendor exit initiative funded |
| D-011 | Stripe handles cards and subscriptions; server/webhooks verify state | Reduces PCI scope; requires reconciliation and provider resilience | Market/provider/business change |
| D-012 | Expo app includes customer and driver roles initially | Shared release/codebase reduces MVP duplication; demands strict role/data separation | Driver workflow/release/native constraints diverge |
| D-013 | Next.js serves public/customer web and admin with separated route groups/build/deploy boundaries as needed | Shared ecosystem without sharing authorization | Security/team/release independence requires split apps |
| D-014 | Push uses Expo/FCM/APNs; SES email provides durable transactional messages; SMS is not default | Pragmatic reach/cost; delivery remains best effort | Demonstrated critical contact gap |
| D-015 | AWS CDK in TypeScript is IaC default | Fits stack skills and repeatable deployments | Operating team standardizes on Terraform before build |
| D-016 | Custody, audit, provider inbox and route versions are append-only; projections are derived | Defensible history, retry safety, disputes | Never casually revisit; corrections append |
| D-017 | No real-time precise driver map for customers in MVP | Minimization and driver safety; ETA/status serves user need | Validated need with privacy/safety design |
| D-018 | Dispatch reviews route before publish | MVP operational safety and learning | Solver/runtime evidence supports bounded auto-publish |

## 3. Working assumptions/defaults to validate

| ID | Assumption/default | Why needed now | Validation |
|---|---|---|---|
| A-001 | Customers prepare, seal and obtain valid retailer/carrier authorization/label before pickup | Bounds service and liability | User research, retailer variants, counsel/ops policy |
| A-002 | Multiple packages per booking are allowed but each has independent label/identity/state | Common use case and correct custody | Pilot demand and driver usability |
| A-003 | Pickup is normally next day/within 24 hours, not guaranteed same-day | Product context | Capacity economics and customer research |
| A-004 | One depot/start-end model and secure exception storage exist | Route/custody planning requires physical model | Operations site and insurance approval |
| A-005 | Drivers are scheduled/managed by Returnet for pilot; marketplace/earnings is out | Keeps identity/pay complexity out | Business/employment model review |
| A-006 | Customer contact is masked/in-app or managed, not personal driver phone | Safety/privacy | Provider/workflow selection |
| A-007 | Photo + scan is pickup baseline; destination adds receipt/reference when obtainable | Reasonable chain-of-custody evidence | Carrier rules, privacy and claims evidence review |
| A-008 | Background location is only active during working shift/route | Minimization | Platform feasibility and worker/privacy review |
| A-009 | Subscription uses finite configurable entitlement rather than “unlimited” | Protects economics/clarity | Pricing study and terms review |
| A-010 | CAD only for MVP | Single market | Expansion plan |
| A-011 | Route planning is batched with controlled replanning, not continuously global | Stability and cost | Pilot exception frequency |
| A-012 | Production is multi-AZ in a Canadian AWS region if service/provider availability and review permit | Availability/residency preference | AWS service matrix, cost, legal/privacy review |
| A-013 | Draft planning objective RPO ≤15 min / RTO ≤4 h | Enables design/exercise planning | Business impact analysis and proven restore |
| A-014 | WCAG 2.2 AA is the web engineering target | Strong accessible baseline | Qualified audit and applicable obligations |

## 4. Open questions and owners

Owners are accountable functions, to be replaced with named people. `P0` blocks public pilot launch; `P1` should be settled before its implementation milestone; `P2` can be learned in pilot.

| ID | Priority / owner | Question | Needed by |
|---|---|---|---|
| Q-001 | P0 Product + Legal | Exact service promise, terms, cancellation/reschedule/no-show fees, retailer-refund disclaimer, claims process and liability limits? | Phase 0 / launch copy |
| Q-002 | P0 Ops + Insurance + Legal | Eligible/restricted goods, size/weight/value limits, damaged packaging refusal, overnight storage, chain-of-custody evidence, insurance coverage? | Phase 0 / booking rules |
| Q-003 | P0 Privacy/Legal + HR/Ops | Driver employment/contract model and lawful, proportionate location monitoring/consent/dispute process? | Before driver device build/pilot |
| Q-004 | P0 Privacy/Legal | Data map, cross-border/provider assessment, exact retention/deletion, privacy request and incident duties? | Before production data |
| Q-005 | P0 Legal/Content | French/English terms, UX, communications and customer-choice process required for Quebec launch? | Before production copy |
| Q-006 | P0 Finance/Accounting | GST/QST registrations/rates/place of supply, Stripe Tax choice, receipt/credit/refund/subscription accounting and record retention? | Before price implementation |
| Q-007 | P0 Ops | Pilot polygons/postal codes, hours, hard-window sizes, lead/cutoff, capacity units, driver shifts/breaks, depots and secure storage? | Routing/booking configuration |
| Q-008 | P1 Product/Finance | Pay-per-pickup price lines and subscription entitlement/renewal/fair-use/failed-payment/grace policy? | Phase 2 |
| Q-009 | P1 Ops/Product | Supported retailer/carrier/return-method combinations and destination data source/update ownership? | Phase 2–3 |
| Q-010 | P1 Engineering/Privacy | AWS region/account topology and Google/Stripe/Expo data-region/contract configuration accepted? | Phase 1 production design |
| Q-011 | P1 Design/Support | Customer contact attempts, wait duration, accessibility accommodations, safe handoff, notification fallback and support hours? | Phase 2–4 |
| Q-012 | P1 Mobile/Security | Minimum iOS/Android versions, device ownership/management, offline duration, lost-device controls, background modes/store-review plan? | Phase 1 spike |
| Q-013 | P1 Security/Ops | Staff MFA/federation, refund/export approval limits, precise role matrix and break-glass approvers? | Phase 1–2 |
| Q-014 | P1 Engineering/Ops | Expected pilot load/route size/evidence volume and formal availability, latency, RPO/RTO support targets? | Load plan before Phase 6 |
| Q-015 | P1 Product/Legal | Proof shown to customers, dispute window, correction language, electronic signature/attestation need? | Phase 4–5 |
| Q-016 | P2 Data/Ops | Optimizer weights, service-time distributions, traffic buffer, route stability penalty and auto-publish readiness thresholds? | Pilot tuning |
| Q-017 | P2 Product | Is SMS justified for a defined critical flow, with bilingual consent/opt-out and provider selection? | After notification pilot |
| Q-018 | P2 Engineering | When does separate driver app, Aurora/read replicas/RDS Proxy, or service extraction beat current architecture? | Evidence-based review |

## 5. Risk register

| ID | Risk | Likelihood/impact (draft) | Mitigation / signal |
|---|---|---|---|
| R-001 | Package rejected after Returnet accepts custody | Medium / High | Validate label/destination before/at pickup, authorized alternatives, secure custody, clear claims/terms |
| R-002 | Lost/damaged or disputed package | Medium / High | Scan/photo/timestamp/location evidence, inventory reconciliation, access logs, insurance and incident process |
| R-003 | Route plan violates real-world window/hours | Medium / High | Accurate inputs, conservative service/buffers, validator, dispatcher review, runtime risk alerts |
| R-004 | Precise driver tracking is excessive or off-shift | Low–Medium / High | Active consent indicator, server acceptance window, minimal cadence/retention/access, audits |
| R-005 | Payment/service state diverges | Medium / High | Idempotency, webhook inbox, local projection, daily reconciliation, pending state, finance queue |
| R-006 | Bilingual/accessibility defects block service | Medium / High | Design system, key parity, professional review, automated+manual gates, support accommodation |
| R-007 | Third-party outage/quota/cost disrupts operation | Medium / Medium–High | Quota/cost alarms, queues, circuit/failure modes, planning cutoff fallback, provider abstraction |
| R-008 | Offline sync overwrites custody truth | Medium / High | Command log, versions, per-package ordering, immutable events, explicit conflict UI |
| R-009 | Staff over-access evidence/location/refunds | Medium / High | Scoped RBAC, masking, access audit, MFA, approval limits, periodic review |
| R-010 | Subscription economics/abuse unsustainable | Medium / Medium | Finite entitlements, reservation/consumption ledger, pilot cohorts and margin metrics |
| R-011 | Bad address/destination data causes missed service | High / Medium | Confidence/review queues, customer confirmation, curated destination ownership, exception routes |
| R-012 | Over-expansion delays safe pilot | Medium / High | MVP boundary, milestone exits, feature flags, decision register |

## 6. Change-control checklist

Before changing a decision or assumption, identify affected requirements, flows/state machines, schema/migrations, API/events, authorization/data map/retention, bilingual/accessibility copy, provider contracts/cost, tests/fixtures/thresholds, operations/runbooks/training, rollout/rollback, and customer/legal disclosures. Update all linked documents in the same change.

