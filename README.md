# Returnet

Returnet is a bilingual pickup service for online-return packages, launching in Montreal, Quebec. A customer books a pickup window through the web or mobile app; an assigned driver collects the prepared package and delivers it to the carrier, retailer, post office, or other authorized return destination. Returnet records the package's chain of custody and gives the customer status updates through final handoff.

This repository contains the first runnable MVP vertical slice and its product/engineering plan. It is suitable for local demonstration and continued pilot engineering; the [known limitations](#verified-status-and-known-limitations) remain launch blockers.

## Quickstart

Prerequisites: Python 3.12+, Node 22+, pnpm 11+, and Docker Desktop for the PostgreSQL/PostGIS path.

```powershell
Copy-Item .env.example .env
python -m pip install -e ".[dev]"
python -m alembic -c backend/alembic.ini upgrade head
python -m backend.app.seed
python -m uvicorn backend.app.main:app --reload --port 8000
```

In separate terminals, start the outbox worker and clients:

```powershell
python -m backend.app.worker
pnpm install
pnpm --dir apps/web dev
pnpm --dir apps/mobile start
```

The API documentation is at `http://localhost:8000/docs`; web is at `http://localhost:3000`. SQLite is the zero-infrastructure demonstration default. To exercise PostgreSQL/PostGIS semantics, run `docker compose up postgres localstack`, set `RETURNET_DATABASE_URL=postgresql+psycopg://returnet:returnet_local_only@localhost:5432/returnet`, migrate, seed, and test.

### Local-only identities

Pass `X-Returnet-Dev-User` from web/API clients. These identities are created by the seed command:

| Role | Email |
|---|---|
| Customer (French) | `customer@local.returnet.ca` |
| Customer (English) | `customer-en@local.returnet.ca` |
| Driver | `driver@local.returnet.ca` |
| Dispatcher | `dispatch@local.returnet.ca` |
| Administrator | `admin@local.returnet.ca` |
| Support | `support@local.returnet.ca` |
| Finance | `finance@local.returnet.ca` |

Development authentication is rejected during settings validation when the environment is `staging` or `production`. Cognito mode verifies RS256 signatures, issuer, audience/client ID, token use, and expiry against configured JWKS; application roles and locale are always loaded from the database. A real Cognito user pool and pilot identities still need environment configuration and end-to-end sandbox validation.

## Repository layout

- `backend/app` — FastAPI modular monolith, domain services, local worker, fake providers and seed scenario.
- `backend/alembic` — database migration entrypoint and initial schema.
- `backend/tests` — API, lifecycle, property, security, outbox and optional PostGIS integration tests.
- `apps/web` — responsive, bilingual, API-backed customer booking/tracking and operations vertical slice.
- `apps/mobile` — bilingual Expo customer/driver experience with API-backed assigned work, an offline command queue, and device-provider adapters.
- `infra/cdk` — AWS CDK model for network, ECS, RDS/PostGIS, queues, storage, identity, edge/security and monitoring. It does not deploy itself.
- `docs` — authoritative product, architecture, security, operations and test specifications.

## Developer checks

```powershell
python -m ruff check backend
python -m mypy backend/app
python -m pytest --cov=backend.app
pnpm --dir apps/web check
pnpm --dir apps/web build
pnpm --dir apps/mobile check
pnpm --dir infra/cdk check
```

Generate a reviewed OpenAPI snapshot with `python scripts/export_openapi.py`. Infrastructure synthesis is local and does not provision resources: `pnpm --dir infra/cdk synth`.

## Verified status and known limitations

The backend local flow covers fake payment, row-locked capacity booking on PostgreSQL, deterministic route proposal/review/publication, driver assignment authorization, evidence upload, idempotent offline pickup/handoff/exception commands, custody/audit events, webhook deduplication, localized outbox notifications, exceptions, cancellation/rescheduling, and seeded role accounts. Prices, taxes, and subscription quantities are configurable placeholders. A concurrent PostgreSQL last-slot test is included and runs when a PostgreSQL test database is available.

Verification results are recorded in [development and verification](docs/10-development-and-verification.md). The current implementation is a strong pilot vertical slice, not an authorization to launch. Cognito JWT verification and an SQS consumer are implemented behind tested boundaries, but real AWS credentials and staging validation remain. Stripe SDK/signature handling, Google Route Optimization calls, S3 malware/quarantine processing, Expo/SES delivery, DLQ operator tooling, full admin case/refund/configuration UI, production secrets/domains/certificates, native store builds, penetration/accessibility reviews, and approved legal/accounting/insurance policies remain before a public pilot.

## Product shape

- **Customers:** responsive web, iOS, and Android booking and tracking experiences.
- **Drivers:** an initial driver role in the Expo React Native app for assigned work, navigation, scans, evidence, exceptions, and offline-safe status capture.
- **Operations:** a Next.js administration and dispatch dashboard for capacity, assignment, route oversight, exceptions, refunds, and audit review.
- **Platform:** FastAPI, PostgreSQL/PostGIS, SQLAlchemy, Alembic, background workers, and an event/outbox model.
- **Infrastructure:** AWS-first, with ECS Fargate, RDS PostgreSQL, S3/CloudFront, SQS, EventBridge, Cognito, and focused supporting services.
- **External specialists:** Google Maps Route Optimization for the MVP and Stripe for payments and subscriptions.

## Documentation map

Read these documents in order for the most coherent product-to-implementation path:

1. [Product requirements](docs/01-product-requirements.md) — users, outcomes, MVP scope, functional and non-functional requirements, and acceptance criteria.
2. [User flows and rules](docs/02-user-flows-and-rules.md) — booking, pickup, delivery, exceptions, state machines, and business-rule defaults.
3. [AWS system architecture](docs/03-aws-system-architecture.md) — deployable components, trust boundaries, environments, delivery, and recovery.
4. [Data model and API](docs/04-data-model-and-api.md) — domain objects, critical fields, endpoint outline, authorization, concurrency, and events.
5. [Routing, notifications, and tracking](docs/05-routing-notifications-and-tracking.md) — optimization constraints, ETA semantics, dispatch workflow, and chain of custody.
6. [Implementation roadmap](docs/06-implementation-roadmap.md) — ordered milestones, dependencies, exit criteria, and post-MVP sequence.
7. [Test strategy](docs/07-test-strategy.md) — traceability, test pyramid, scenario matrix, thresholds, and production verification.
8. [Security, privacy, and operations](docs/08-security-privacy-and-operations.md) — controls, Quebec/Canadian considerations, observability, incident response, and runbooks.
9. [Decisions, assumptions, and open questions](docs/09-decisions-assumptions-and-open-questions.md) — current decisions, defaults to validate, risks, and unresolved product/legal choices.
10. [Glossary](docs/glossary.md) — canonical terminology used across the set.
11. [Development and verification](docs/10-development-and-verification.md) — runnable workflows, provider boundaries, verification record, and implementation limitations.

## How to use these documents to build the product

1. Product, operations, engineering, design, legal, and accounting review the requirements and the assumptions log. Resolve only the decisions that block the next milestone; retain an owner and target date for the rest.
2. Convert the requirement IDs (`PR-*`, `FR-*`, `NFR-*`) and acceptance criteria into epics and testable stories. Link each story to the relevant flow, API operation, and test case.
3. Establish the architecture skeleton, environments, identity, migrations, and observability before feature work. Implement vertical slices in the roadmap order rather than building each frontend or service in isolation.
4. Treat state transitions and ledger-like records as the source of truth. UI labels, notifications, analytics, and support tools should derive from those records rather than inventing parallel status models.
5. Run the test gates in [the test strategy](docs/07-test-strategy.md) at each milestone. Record any changed threshold as an explicit decision rather than silently weakening it.
6. Update these documents with implementation discoveries. Architecture changes should be recorded in the decisions log (and promoted to an ADR when consequential); business-rule changes must update flows, APIs, and tests together.

## MVP boundary

The target MVP supports one Montreal service area, one operating organization, prepared and labelled standard packages, scheduled pickup windows, card payments and a simple monthly plan, manually supervised dispatch with automated route proposals, bilingual customer experiences, push/email notifications, and evidenced final handoff. The current vertical slice demonstrates those boundaries in local mode but still requires the external launch work listed above, including real provider delivery and native-device verification. It does not initially promise instant/on-demand pickup, marketplace driver onboarding, cash, multi-package consolidated labels, returns without retailer authorization, or fully autonomous exception resolution.

## Status and cautions

This is a coherent implementation baseline, not a final statement of commercial policy. Prices, service areas, tax treatment, retention periods, insurance coverage, restricted-goods policy, accessibility conformance evidence, and legal wording require validation by qualified Quebec/Canadian professionals and operational pilots. ETA messages are estimates, never guaranteed arrival commitments.
