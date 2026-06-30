## Product Requirement Document

Hey team, we need to build out that HTTP client toolkit we've been talking about. The goal is basically to let our app devs stop writing all that repetitive glue code every time they spin up a new service — you know, the stuff where everyone hand-rolls their own URL building, param encoding, header juggling, etc. It always ends up slightly broken in some edge case.

The toolkit should handle building requests declaratively, deal with the auth token situation automatically when the server pushes back (similar to how we handled the refresh flow in the old login module, check that for reference), and support attaching middleware so teams can inject stuff like tracing headers without touching the core logic.

We also need decent logging — both for outbound requests and what comes back — and a way to render requests as copy-pasteable shell commands for debugging. On the data side, it needs to handle nested structures and collections in query params, not just flat key=value stuff. There's also a file upload scenario we need to support, but only byte-array payloads — if someone tries to pass something weird there it should fail cleanly without leaking internal error details.

The whole thing should be organized properly across multiple files, not one giant blob. Output from the adapter layer should always be deterministic and machine-readable. Let's get a proper breakdown of what needs to be built.