## Product Requirement Document

Hey team, we need to build out that HTTP test double toolkit we've been talking about. The idea is that devs can spin up fake request/response objects in their handler tests without needing a real server running. Think of it like what we did for the login module's compatibility shims, but for the full HTTP layer.

On the request side, people need to be able to set things like headers, route params, body, cookies, and so on. Header reads should work regardless of how the dev capitalizes things — we got a bug report last sprint where someone's tests kept failing because of casing inconsistencies. Also the referrer thing keeps coming up (you know, the two spellings), make sure that's handled. There's also some content negotiation stuff — Accept headers, encoding preferences, language, charset — all that should resolve against a list of candidates the dev provides.

Range parsing is needed too; if the range is outside the file size it should give back some kind of negative signal rather than throwing, and absent ranges should be distinguishable from bad ones.

On the response side, cookies need to support a 'clear' operation that sets an expiry in the past. Also need redirect, render, JSON/JSONP send, write/end chunking, header management (append, remove, vary de-dup), and a format-negotiation helper that falls back to 406 if nothing matches.

Parameter resolution should check route params first, then body, then query — and falsy values like 0 should not be skipped over.

A couple follow-ups from the questions that came in. For a brand new request, the defaults should be method GET, empty string for url/original_url/base_url/path, empty objects for params/cookies/headers/body/query/files, and absent (undefined/null) for session and signed_cookies. Also, if createRequest() gets a path option but no url option, that path should show up as the observable url field on the request object.

On headers, the behavior should be fully case-insensitive across the board. That means the direct lookup method, like req.get(), and any aliased method should return the stored value no matter how the header was originally stored or how it’s looked up later. If the header isn’t there, just return an absent value like undefined, never throw. Same deal for the referrer/referer alias behavior we talked about before.

For ranges, the negative signals should be exact: use -1 for unsatisfiable ranges (start > size-1) and -2 for malformed/unparseable Range header strings. That keeps absent ranges distinct from bad ones, which is what we want.

A few response specifics too. Calling sendStatus(code) should set the status code, set the Content-Type header to 'text/plain', set the body data to the standard HTTP status message string for that code, like 404 → 'Not Found', and mark the response as ended with ended=true, headers_sent=true, writable_finished=true. For JSON helpers, res.json() sets Content-Type to 'application/json' and res.jsonp() sets Content-Type to 'text/javascript'. Both should serialize the value to a JSON string, store that as body data, and both mark the response as ended.

For redirects, redirect(url) should default to status 302, while redirect(status, url) uses whatever status is supplied. In both cases, emit 'end' and 'finish' and record the redirect URL so tests can inspect it later. For res.format(), it takes a map of media-type keys to handler functions and should run the first handler whose key matches the request’s Accept header. If nothing matches and there’s no 'default' key, set the response to status 406 (Not Acceptable).

On streaming-ish behavior, res.write(chunk, encoding?) should append string chunks into a string data accumulator and Buffer chunks into a separate buffer accumulator. The encoding from the first write call is the one we record, and headers_sent flips to true on that first write. Then res.end(chunk?) can append one last chunk if there is one, and after that it sets ended=true and writable_finished=true.

Last thing, for Vary handling, please de-dup values so adding the same field name more than once doesn’t create duplicates, and that comparison should be case-insensitive.