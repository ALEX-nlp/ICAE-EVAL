## Product Requirement Document

We need a reusable client library that lets mobile application developers communicate with a social-media backend without hand-writing HTTP requests. The library should support looking up user profiles, browsing posts and feeds, managing social relationships (follow, unfollow, approve or reject follow requests), interacting with content (likes, comments), and participating in live broadcasts.

Credentials submitted during login must be obfuscated before leaving the device — implement the same approach used by the authentication module. Large numeric identifiers must survive JSON round-trips without precision loss, so the response parser must convert any integer beyond the platform safe range into its exact decimal string form.

For listing operations (feeds, followers, posts in a hashtag, category browsing, search), the library should inject sensible pagination defaults automatically so callers don't repeat them; certain feed types use a smaller default page size with extra selector constants. Write operations fall into two categories: some use a URL-encoded form body while others carry a structured nested object body.

Starting a live broadcast is a two-step orchestration: first create the room, then activate it. If either step fails the error must surface as a clear normalized category string, not a raw runtime exception. Configuration validation should also fail fast with category strings.

The test adapter must report the exact HTTP method, path, query parameters, and body the library assembled, plus the parsed response, with all output keys sorted alphabetically.