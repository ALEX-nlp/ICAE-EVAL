## Product Requirement Document

Hey team, we need to build out this token service library thing that our backend guys have been asking about. Basically it needs to handle those self-contained auth tokens that get passed around between services — you know, the compact dot-separated ones that go in URL params and headers. The core ask is: sign tokens with a shared secret, verify them later, and make sure bad tokens fail loudly with consistent error messages (not random stack traces or whatever the Java runtime decides to spit out that day).

Important stuff: we need to support the whole HMAC family (the 256/384/512 variants), and also the 'no signature' flavor for internal tooling. There's also a compression feature someone requested — refer to how we handled the codec abstraction in that streaming pipeline project, it should be similar vibes.

On errors: the PM from the security team specifically called out that we must block the 'algorithm swap' attack where someone sneaks in a forged token using a public key as a MAC secret. That has to hard-fail, not silently pass.

Also need time-based validity (expiry + not-before), required-claim enforcement, and the adapter layer needs to speak a flat key=value format over stdin/stdout — no JSON in the output. Registered claim names use short forms. Custom claims need a prefix. Dates go out as integer seconds. Don't leak any internal exception info.