## Product Requirement Document

Hey team, we need a small telemetry SDK for our C++ services. The idea is pretty simple: devs give it one connection string and it handles all the boring stuff — figuring out where to send events, stamping them with IDs and times, and shipping them off. We had something like this for the Python side (remember that DSN parsing logic we did for the analytics pipeline?), so hopefully we can follow a similar pattern here.

The SDK needs to support reporting plain log messages, caught and uncaught exceptions, and a breadcrumb trail leading up to each event. Context data should be mergeable into events. Error handling for bad connection strings is important — users keep misconfiguring their endpoints in prod and it causes silent failures, which is a nightmare to debug.

Architecturally, keep it clean — transport, event building, and metadata generation should live in separate units. The test harness reads JSON from stdin and writes results to stdout, and network calls must go to an in-memory sink during tests so nothing actually hits the wire.

One thing I'm fuzzy on: the exact format for event IDs and timestamps — there were some specific rules discussed in the last infra sync that I didn't fully catch. Also not sure about the exact structure for the ingest endpoint URL. Can someone clarify those details when the work starts?