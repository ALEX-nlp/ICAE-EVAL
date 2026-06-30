## Product Requirement Document

Hey team, we need to build out that HTTP test double toolkit we've been talking about. The idea is that devs can spin up fake request/response objects in their handler tests without needing a real server running. Think of it like what we did for the login module's compatibility shims, but for the full HTTP layer.

On the request side, people need to be able to set things like headers, route params, body, cookies, and so on. Header reads should work regardless of how the dev capitalizes things — we got a bug report last sprint where someone's tests kept failing because of casing inconsistencies. Also the referrer thing keeps coming up (you know, the two spellings), make sure that's handled. There's also some content negotiation stuff — Accept headers, encoding preferences, language, charset — all that should resolve against a list of candidates the dev provides.

Range parsing is needed too; if the range is outside the file size it should give back some kind of negative signal rather than throwing, and absent ranges should be distinguishable from bad ones.

On the response side, cookies need to support a 'clear' operation that sets an expiry in the past. Also need redirect, render, JSON/JSONP send, write/end chunking, header management (append, remove, vary de-dup), and a format-negotiation helper that falls back to 406 if nothing matches.

Parameter resolution should check route params first, then body, then query — and falsy values like 0 should not be skipped over.