## Product Requirement Document

Hey team, we need to build out that cloud storage adapter library we've been talking about. Basically devs are tired of writing the same glue code every time they wire up a new storage backend — parsing connection strings, dealing with encrypted credentials, figuring out what capabilities a driver exposes, validating config maps before they blow up at runtime, etc. It's a mess and every team does it differently.

The library should cover the main integration points: parsing those listener address strings (you know the ones, like the format we standardized after the infra incident last quarter), doing encrypt/decrypt round trips for secrets (similar to how we handled it in the auth module, ask Priya if you need context), checking driver identity and what operations it supports, validating option maps with all the conditional/dependency logic, building volume sources from shared filesystem responses, handling access grants over HTTP, and parsing those user agent flags from CLI args.

For errors, we want consistent normalized category names — no raw exception messages leaking out. Output should be stable and deterministic so it's testable. The library needs to be structured properly, not just one giant file — separate concerns, keep the I/O adapter layer away from the business logic. Think production-grade repo layout.

We'll need this to pass the integration test suite in rcb_tests. Ping me if anything's unclear but please check the existing test files first before asking obvious stuff.