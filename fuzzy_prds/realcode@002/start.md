## Product Requirement Document

Hey team, we need a small HTTP utility library — think something like the tiny fetch polyfill approach we used in the login module a while back, but more formalized. The core idea is: one function, you pass it a URL and some options, you get a promise back. It has to work the same whether the code runs in a browser or on a server, without the caller needing to know which environment they're in. The resolver should just figure it out automatically.

The response object needs to let you read the body (text or structured data), inspect where the response actually came from (since redirects happen), copy the response if you need it in more than one place, and look up headers without worrying about casing issues — our support team keeps getting bug reports about headers being silently dropped because of case mismatches.

On the server side, there's a known issue where protocol-relative links cause requests to fail silently — we've had a couple of incidents around this so it needs to be handled. Also, if the runtime already has a built-in HTTP client, we should obviously just use that instead of our own engine, and it shouldn't break if called in a detached way.

The whole thing should be cleanly split up — don't just dump everything in one file. There should be a separate adapter layer that handles the stdin/stdout test interface so the core logic stays clean.