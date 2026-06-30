## Product Requirement Document

Hey team, we need to build out that caching utility layer we've been talking about for the web app. Basically devs are super frustrated right now because every time they need to cache something — whether it's a computed value, an API response, or a chunk of rendered HTML — they're rolling their own logic and it's all inconsistent. We keep getting bugs where stale data shows up or the same thing gets computed like 5 times when it shouldn't be.

The core idea: one unified caching adapter that handles storing key/value pairs, wrapping functions so their results get reused, caching HTTP route responses (think query string normalization like we did in that search endpoint refactor last quarter), and template fragment caching. We also need proper lifecycle stuff — like being able to check if something exists, remove things in bulk, and have values automatically go away after a while.

Also important: when you set the thing up, later config should win over earlier config — similar to how the auth middleware init works. And if someone passes bad config (like a network backend with no host), we want a clean, non-framework-specific error, not a raw Python exception blowing up in prod.

Function caching needs to be smart about arguments — if someone calls the same function with args in different orders or using keyword vs positional style, it should still hit the cache. Same deal for HTTP query strings.

Let's keep it clean and modular. More details to come but wanted to get this filed.