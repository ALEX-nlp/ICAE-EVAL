## Product Requirement Document

We need a reusable client library that lets mobile application developers communicate with a social-media backend without hand-writing HTTP requests. The library should support looking up user profiles, browsing posts and feeds, managing social relationships (follow, unfollow, approve or reject follow requests), interacting with content (likes, comments), and participating in live broadcasts.

Credentials submitted during login must be obfuscated before leaving the device — implement the same approach used by the authentication module. Large numeric identifiers must survive JSON round-trips without precision loss, so the response parser must convert any integer beyond the platform safe range into its exact decimal string form.

For listing operations (feeds, followers, posts in a hashtag, category browsing, search), the library should inject sensible pagination defaults automatically so callers don't repeat them; certain feed types use a smaller default page size with extra selector constants. Write operations fall into two categories: some use a URL-encoded form body while others carry a structured nested object body.

Starting a live broadcast is a two-step orchestration: first create the room, then activate it. If either step fails the error must surface as a clear normalized category string, not a raw runtime exception. Configuration validation should also fail fast with category strings.

The test adapter must report the exact HTTP method, path, query parameters, and body the library assembled, plus the parsed response, with all output keys sorted alphabetically.

One extra pass on the details the team asked about: for the credential obfuscation, use the same behavior as in golden/src/cryptography.ts — function `encryptWithXOR(value: string, key = 5)` which XORs each character's code point with the key (default 5) and joins lowercase hex fragments. The default XOR key is the integer 5, the cipher applies `charCodeAt(0) ^ 5` for each character and converts the result to lowercase hexadecimal, and when no key argument is provided, 5 is used. Also on login, the params template should start with exactly `mix_mode: 1`, `username: ""`, `email: ""`, `mobile: ""`, `account: ""`, `password: ""`, `captcha: ""`, and then the encrypted credentials only replace the fields that matter for that mode, so email mode updates email+password, username mode updates username+password, and everything else stays as the empty-string default.

A couple parser specifics too: when the raw payload is an empty string, or really any falsy/zero-length value, just return it unchanged and do not try to parse it. The expected output there is `{"parsed":""}` — the empty string comes back as-is, not null or undefined. For normal JSON parsing, any integer whose magnitude is beyond the JavaScript safe integer range should be preserved as its exact decimal string, using `JSONBig({ storeAsString: true }).parse(data)`. Number.MAX_SAFE_INTEGER = 2^53 - 1 = 9007199254740991 is the cutoff reference here. Small integers like `0`, `1`, `50` remain as numbers.

For listing calls, the base defaults are `count: 20` and `retry_type: "no_retry"`, and they get merged before the caller’s params so the caller can still override them. The string value for retry_type is exactly `"no_retry"`.

On the live flow, if the create-room response comes back with a non-zero `status_code`, stop there and return `{"error": "live_stream_room_not_created"}`. If room creation works but activation fails, return `{"error": "live_stream_not_started"}`. In those error cases, the `requests` array should only include the requests that were actually issued up to the point of failure.

Two config-related fail-fast cases also need to be explicit. If the client is created without a `signURL` function in config, it should throw immediately and normalize that as `"missing_sign_url"`. Separately, if a request is made without a `paramsSerializer` function on that request config, normalize it as `"missing_params_serializer"`.

Last thing on auth state: after a successful login POST, if the response headers include `x-tt-token`, store that value at `this.request.defaults.headers.common['x-tt-token']` so later requests send it automatically. The output token field should be the captured header value, or `null` if that header was not present.