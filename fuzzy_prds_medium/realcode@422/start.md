## Product Requirement Document

Hey team, we need a small telemetry SDK for our C++ services. The idea is pretty simple: devs give it one connection string and it handles all the boring stuff — figuring out where to send events, stamping them with IDs and times, and shipping them off. We had something like this for the Python side (remember that DSN parsing logic we did for the analytics pipeline?), so hopefully we can follow a similar pattern here.

The SDK needs to support reporting plain log messages, caught and uncaught exceptions, and a breadcrumb trail leading up to each event. Context data should be mergeable into events. Error handling for bad connection strings is important — users keep misconfiguring their endpoints in prod and it causes silent failures, which is a nightmare to debug.

Architecturally, keep it clean — transport, event building, and metadata generation should live in separate units. The test harness reads JSON from stdin and writes results to stdout, and network calls must go to an in-memory sink during tests so nothing actually hits the wire.

One thing I'm fuzzy on: the exact format for event IDs and timestamps — there were some specific rules discussed in the last infra sync that I didn't fully catch. Also not sure about the exact structure for the ingest endpoint URL. Can someone clarify those details when the work starts?

Quick follow-up after the questions that came in: for the connection string, the accepted shape is scheme://public_key:secret_key@host/project_id. The scheme must be either http or https, and the project_id must be a numeric segment. If it’s anything else — missing scheme, unsupported scheme, missing public key, missing secret key, missing credentials entirely, or a missing/empty project segment — we should reject it right when constructing the client with error=invalid_dsn and echo the original input back as dsn=<raw>.

On the endpoint piece I was fuzzy about, the ingest URL should be built as scheme://host/api/<project_id>/store/. Keep the original scheme, strip the credentials, and place the project_id into that path. So for example, https://abc:def@sentry.io/123 becomes https://sentry.io/api/123/store/. Also, when I said Feature 1 before, that’s specifically the connection-string parsing and validation logic around scheme://public_key:secret_key@host/project_id plus the derived endpoint URL scheme://host/api/<project_id>/store/.

For the architecture side, the reporting core should depend on a transport abstraction, not a concrete HTTP implementation. Real HTTP and the in-memory test sink both need to be swappable behind that same interface, and in tests the adapter should route all network egress into the in-memory sink so we can inspect events deterministically and never make real HTTP calls.

The event ID and timestamp rules are also now clear. The event identifier is a 32-character string made only of lowercase hexadecimal digits, and index 12 must always be the version marker character '4'. It should be newly generated for every event. The human-readable timestamp is exactly 20 characters, in UTC, using extended ISO-8601 as YYYY-MM-DDTHH:MM:SSZ, with the mask ####-##-##T##:##:##Z.

Last little test harness detail: the suite runs with 'bash rcb_tests/test.sh' and it can take an optional '--cases-dir <subdir>' argument, with default: public_test_cases. For each case it writes stdout to rcb_tests/stdout/<cases-dir>/<filename_stem>@<zero_padded_index>.txt, for example rcb_tests/stdout/public_test_cases/feature1_1_endpoint_derivation@000.txt.