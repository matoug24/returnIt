# Glossary

[Documentation index](../README.md) · [Decisions and open questions](09-decisions-assumptions-and-open-questions.md)

Canonical terms used throughout the Returnet documentation:

- **Active route:** a published route whose driver has started execution.
- **Booking:** the customer/commercial arrangement for one pickup address and scheduled window; it may contain multiple packages.
- **Capacity bucket:** versioned availability for a service zone, date, and hard window, consumed in configured units.
- **Case:** an owned support/operations/claim record appended to a booking or package timeline.
- **Chain of custody:** the evidenced chronological record of who controlled a physical package from accepted pickup through destination handoff or another terminal resolution.
- **Confirmed pickup window / hard window:** the earliest/latest interval Returnet commits to use as a routing constraint. It is not an exact appointment.
- **Custody event:** immutable fact recording an attempted or completed transfer, exception, or resolution for one package.
- **Destination:** the authorized carrier, retailer, post office, locker, or other return location for a package.
- **Entitlement:** a subscription benefit that can be available, reserved, consumed, released, or expired independently of Stripe's billing state.
- **Estimated arrival / ETA:** a calculated, timestamped range based on current information; it is an estimate, not a promise and does not replace the confirmed window.
- **Evidence:** a scan, photo, receipt/reference, timestamp, permitted geolocation, or attestation supporting an operational/custody fact.
- **Handoff:** transfer of an in-custody package to its authorized return destination, supported by configured evidence.
- **Idempotency:** property that retrying the same identified operation has the same semantic effect and does not duplicate side effects.
- **Notification outbox:** durable record created with a domain transaction and later used to request customer communication.
- **Package:** one independently identifiable physical return item with its own eligibility, label/destination, custody, evidence, and outcome.
- **Preferred time:** customer-selected target inside the hard pickup window. It is a weighted optimization goal and is not guaranteed.
- **Proof:** customer/support-facing, appropriately redacted presentation of chain-of-custody evidence; it is not itself the source event.
- **Route:** a driver's work for a service period. Every proposal/publication is an immutable route version.
- **Route freeze:** configurable planning cutoff after which changes are more controlled and stability is valued.
- **Service time:** planned/actual non-driving time required to complete a stop.
- **Service zone:** versioned geographic and operating-policy boundary in which Returnet offers service.
- **Stop:** ordered pickup, destination, break, or depot action in a route version. One stop may handle multiple packages.
- **Transactional outbox:** database records written atomically with domain changes, then reliably relayed to asynchronous consumers.

