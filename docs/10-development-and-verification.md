# 10 — Development and verification

[Documentation index](../README.md) · [Implementation roadmap](06-implementation-roadmap.md) · [Test strategy](07-test-strategy.md)

## Implemented vertical slice

The repository implements a coherent local demonstration across customer booking, fake card/subscription entitlement, capacity, dispatch route planning/publication, assigned-driver evidence and custody commands, destination handoff, immutable audit/outbox records, localized notification sink, and customer/operations views. The API uses stable versioned routes, request IDs, consistent error envelopes, resource versions, ownership/role checks, command IDs, and idempotency records.

External providers are explicit ports or configuration boundaries. Local mode is deterministic and requires no paid credentials. Production adapter work that would contact Stripe, Google, AWS, Expo/FCM/APNs, or SES is intentionally not activated.

## Local workflows

### Fast SQLite demo

Follow the root quickstart. The seed creates the Montreal window, all roles, a paid sample booking, a dispatcher-reviewed published route, and notification records. Re-running seed is safe and does not duplicate data.

### PostgreSQL/PostGIS integration

```powershell
docker compose up -d postgres localstack
$env:RETURNET_DATABASE_URL='postgresql+psycopg://returnet:returnet_local_only@localhost:5432/returnet'
python -m alembic -c backend/alembic.ini upgrade head
python -m backend.app.seed
python -m pytest -m postgres
```

The environment variable assignment is session-local. Do not reuse the Compose password outside local development.

### End-to-end demo

1. Open the Next.js customer page and book with the seeded customer. Fake payment succeeds deterministically.
2. Open Operations; create a route proposal through the API and publish it after review. Hard-window output is revalidated at publish time.
3. Open the Expo driver role, create scan/photo evidence and enqueue pickup/handoff commands. The queue deduplicates command IDs and stops on version conflict.
4. Run the worker. Local notification records are emitted once per semantic event/version in the booking locale.
5. Inspect the customer timeline/API, custody events, evidence metadata, notifications, and audit events.

## Provider configuration boundaries

- **Stripe:** `RETURNET_PAYMENT_PROVIDER=fake` is runnable. `stripe` mode refuses missing credentials, but SDK signature/provider operations remain a production task.
- **Routing:** local deterministic ordering respects hard windows, preferred-time ordering, service duration, shift and weight capacity. Google project configuration is reserved; a live adapter is not invoked.
- **Notifications:** local sink persists bilingual messages. Expo/FCM/APNs and SES credentials/delivery receipt workers remain external adapter work.
- **Evidence:** local storage enforces ownership, file type and size. CDK provides private encrypted S3; presigned S3 and malware scanning remain to complete.
- **Authentication:** local header identities are limited to development/test by startup validation. Cognito mode verifies RS256 JWKS signatures, issuer, audience/client ID, token use, and expiry, then obtains the authoritative role/locale from the database. Real-pool integration and federation remain environment work.
- **Queue:** transactional outbox and local retry-safe processing are implemented. The SQS long-poll adapter deletes messages only after successful handling, while CDK creates and wires SQS/DLQ/EventBridge. Real AWS staging, publisher integration, and DLQ operator tooling remain.

## Verification record

Record results after running commands rather than assuming success:

| Check | Result in this implementation environment |
|---|---|
| Python compile | Passed on Python 3.13 |
| Ruff lint | Passed |
| MyPy strict | Passed for `backend/app` |
| Pytest + coverage | 20 passed, 2 PostgreSQL/PostGIS-only skips; 85.55% statement coverage |
| Alembic SQLite upgrade | Passed from an empty database; deterministic seed and readiness smoke passed |
| PostgreSQL/PostGIS | Not run: Docker CLI is unavailable on this host; CI/Compose test is defined |
| Web lint/type/test/build | Passed: ESLint, TypeScript, 2 Vitest tests, and Next.js production build |
| Mobile type/test | Passed: TypeScript, 2 Jest suites, and 5 tests covering queue replay, endpoint mapping, development auth, and localization; native iOS/Android builds not run on this Windows host |
| CDK build/test/synth | Passed: TypeScript, 3 assertions, and local CloudFormation synthesis; no deploy performed |
| Lockfile reproducibility | Passed: `pnpm install --frozen-lockfile --offline --ignore-scripts` reports the workspace up to date |
| OpenAPI and documentation | OpenAPI 3.1 snapshot exported and parsed with 27 paths and 28 operations; all local Markdown links resolve |

## Known limitations and launch blockers

- SQLite demonstration cannot execute PostgreSQL locking, isolation, PostGIS, concurrent last-slot behavior, or query plans. The implementation uses PostgreSQL `SELECT ... FOR UPDATE` for capacity, route publication, and finance adjustment contention and includes a concurrent last-slot integration test; run the PostgreSQL suite in CI and before pilot.
- Subscription entitlement is a deterministic finite pilot allowance, not a full period ledger. Refund/credit/case/configuration models and complete UIs remain.
- ETA copy and confidence/staleness/threshold hysteresis decision logic are implemented and property/unit tested, but state persistence, live sampling and route-delay propagation require the real routing/location worker.
- Mobile uses testable camera/location providers, secure token storage, API-backed customer bookings and assigned driver work, evidence metadata creation, and offline pickup/handoff/exception replay. Native permissions, background behavior, navigation, mobile booking entry, and physical-device builds require platform verification.
- Web booking, tracking/proof, and operations screens are bilingual and API-backed. Professional French-language review and end-to-end accessibility testing remain launch gates.
- Evidence file checks do not yet calculate/verify the declared checksum or perform malware/metadata processing.
- AWS CDK uses cost-conscious defaults and a deployment parameter; certificates, DNS, alarms to an on-call destination, production scaling, backup/RPO settings and multi-region choices require environment review.
- Legal, privacy, French-language, tax, accessibility, insurance, restricted-goods and worker-monitoring decisions in [the open-question register](09-decisions-assumptions-and-open-questions.md) remain authoritative launch gates.
