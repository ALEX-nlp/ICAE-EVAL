## Product Requirement Document

Hey team, we need to build out the recaptcha verification client library. Basically the idea is that right now devs have to hand-roll all the request building, response parsing, and validation logic themselves and it's a mess — people keep missing edge cases around stale challenges or mismatched hostnames and we keep getting bug reports about it. We want a clean client that handles all of that in one place.

The library needs to validate the shared secret upfront (similar to how we handled the auth token checks in the payment gateway module — check that code for reference), build the outbound request payload, parse whatever the verification service sends back, run some optional local checks on the parsed result, and support at least two different ways of actually sending the request over the network.

One thing that's been causing production issues lately is that users are completing the challenge but then the backend is accepting it way too long after the fact — we need some kind of freshness enforcement on that. Also there have been complaints that the library crashes with cryptic internal errors instead of returning something the caller can actually handle gracefully.

The response format needs to be consistent across all operations and the two transport strategies need to be swappable without changing the core logic. Reach out if anything is unclear, but try to check the existing test fixtures first before pinging me.