## Product Requirement Document

Hey team, we need a small Dart client library for handling user auth against our identity backend — no heavy SDKs, just plain HTTP/JSON. The rough scope is: looking up what login methods an email already has, registering new accounts, signing in, deleting accounts, and a tiny local storage thing for caching session data between runs.

The tricky part is error handling — when the backend sends back failure codes, we can't just bubble up raw backend strings to the UI layer. There was a ticket about this a while back (similar to that normalization pattern we used in the login module), so make sure we follow the same convention there.

Also for testing purposes, we need a way to swap out the actual HTTP calls with fake/canned responses so we can run tests offline without hitting a real server. The adapter layer should read a JSON command from stdin and print results to stdout so we can drive it from test scripts.

One thing I keep getting questions about from the frontend team — when we register a new user, there's apparently a two-step process on the backend side (create account, then fetch profile), and we need to merge those into one response. Make sure the output fields are in the right order, they said last time we got tripped up on that.

For the local storage piece, there was some confusion about what happens when you try to read a key that was never written — just make sure it's handled consistently with the rest of our error reporting.

One extra pass on the auth error piece since a couple people asked: the normalization rule is just to lower-case the backend error code string and replace all underscores with hyphens, and we do that uniformly across all auth error responses that come through the adapter. So INVALID_IDENTIFIER becomes invalid-identifier, EMAIL_NOT_FOUND becomes email-not-found, and USER_NOT_FOUND becomes user-not-found. Same idea everywhere, no special cases.

Also confirming the sign_up output because the order matters here. A successful sign_up action prints exactly seven lines in this fixed order: email=<email>, uid=<localId>, is_new_user=true, provider_id=<sign-in provider from providerUserInfo>, is_anonymous=<true|false> (true only when providerUserInfo is empty), provider_count=<number of linked providers>, creation_time_ms=<createdAt as an integer>. The order is strict and must not vary.

On the fake transport/testing side, the intent is dependency inversion: the core engine depends on an abstract transport interface, not a concrete HTTP client. For offline/test runs, the adapter gets a responses map in the JSON input keyed by role names like lookup, register, account, credential, remove. Each role entry has a status integer and a body object, and the test double transport just intercepts calls by role key and returns that canned status and body without making any real network requests.

And just so nobody has to infer which role goes with which action: fetch_providers uses 'lookup'; sign_in uses 'credential'; sign_up uses 'register' for account creation and 'account' for the profile fetch; delete_account uses 'register', 'account', and then 'remove' for the deletion call, since it has to establish the signed-in user first the same way sign_up does. The store action does not use any responses map.