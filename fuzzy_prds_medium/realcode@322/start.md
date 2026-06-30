## Product Requirement Document

Hey team, we need to build out this token service library thing that our backend guys have been asking about. Basically it needs to handle those self-contained auth tokens that get passed around between services — you know, the compact dot-separated ones that go in URL params and headers. The core ask is: sign tokens with a shared secret, verify them later, and make sure bad tokens fail loudly with consistent error messages (not random stack traces or whatever the Java runtime decides to spit out that day).

Important stuff: we need to support the whole HMAC family (the 256/384/512 variants), and also the 'no signature' flavor for internal tooling. There's also a compression feature someone requested — refer to how we handled the codec abstraction in that streaming pipeline project, it should be similar vibes.

On errors: the PM from the security team specifically called out that we must block the 'algorithm swap' attack where someone sneaks in a forged token using a public key as a MAC secret. That has to hard-fail, not silently pass.

Also need time-based validity (expiry + not-before), required-claim enforcement, and the adapter layer needs to speak a flat key=value format over stdin/stdout — no JSON in the output. Registered claim names use short forms. Custom claims need a prefix. Dates go out as integer seconds. Don't leak any internal exception info.

One extra pass on the output/details since a few folks asked the same questions: custom claims need to come out as 'claim.' plus the claim name, like 'claim.role=admin'. Those always show up after the registered claims, and they need to be sorted in ascending key order. The registered ones should use the short keys exactly as-is: iss, sub, aud, jti, exp, nbf, iat. Those come first in output, in that canonical order, and the date ones exp, nbf, iat should be normalized to integer seconds since the Unix epoch.

Related to that, if exp, nbf, or iat come in on input, treat them as milliseconds since the Unix epoch and then store/output them as integer seconds since the Unix epoch. So the example to keep in mind is 9999999999000 ms → 9999999999 seconds. For required claims, if the claim exists but the value is wrong, return 'error=incorrect_claim' and then 'claim=<name>'. If it’s not there at all, return 'error=missing_claim' and then 'claim=<name>'.

For the adapter format, it really is just flat key=value lines, one per line, separated by newline characters. No JSON, no XML, no brackets, and no host-language exception text or stack traces sneaking through. Same ordering rule there too: registered claims first in iss, sub, aud, jti, exp, nbf, iat order, then custom claims sorted ascending by key with the 'claim.' prefix.

A couple parser edge cases to lock down: if a token does not have exactly two period separators and therefore does not produce exactly three segments, return 'error=malformed' followed by 'reason=period_count'. If the period count is right but the body segment is empty, return 'error=malformed' followed by 'reason=missing_body'.

Also on algorithm lookup, when we’re resolving by name with op=algorithm_for_name, if the name isn’t recognized, return 'error=signature_invalid' and nothing else. Known algorithm names should resolve case-insensitively.

And on compression, the intended behavior is the same codec abstraction pattern from the compression codec abstraction in rcb_tests/dispatcher supporting DEF (DEFLATE), GZIP, and CUSTOM codecs — specifically the compress_roundtrip operation in feature5 which requires registering a custom Compression codec by name and using it transparently during parse.