## Product Requirement Document

Hey team, we need a small Dart client library for handling user auth against our identity backend — no heavy SDKs, just plain HTTP/JSON. The rough scope is: looking up what login methods an email already has, registering new accounts, signing in, deleting accounts, and a tiny local storage thing for caching session data between runs.

The tricky part is error handling — when the backend sends back failure codes, we can't just bubble up raw backend strings to the UI layer. There was a ticket about this a while back (similar to that normalization pattern we used in the login module), so make sure we follow the same convention there.

Also for testing purposes, we need a way to swap out the actual HTTP calls with fake/canned responses so we can run tests offline without hitting a real server. The adapter layer should read a JSON command from stdin and print results to stdout so we can drive it from test scripts.

One thing I keep getting questions about from the frontend team — when we register a new user, there's apparently a two-step process on the backend side (create account, then fetch profile), and we need to merge those into one response. Make sure the output fields are in the right order, they said last time we got tripped up on that.

For the local storage piece, there was some confusion about what happens when you try to read a key that was never written — just make sure it's handled consistently with the rest of our error reporting.