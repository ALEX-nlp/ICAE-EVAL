## Product Requirement Document

Hey team, we need to build out the i18n catalog loading runtime we've been talking about. Basically the idea is that developers shouldn't have to hand-roll all that locale file picking, parsing, merging, and key traversal logic every time. We want a single layer that handles all of that.

The system needs to support loading translations from local files in at least two formats (you know, the usual suspects), and also from a remote source abstraction — same output shape either way. When a locale file isn't available, it should gracefully fall back to a default instead of blowing up. We also need that deep-merge behavior we discussed, like what we did with the fallback handling in the login module last time, where the active locale values win but missing keys still come through from the fallback.

For grouped catalog loading, there should be some kind of namespace support, and we need to validate the input before even attempting the load — fail fast, clean error, no stack traces leaking out.

Key resolution needs to handle nested paths using a configurable separator, and plural variants should be selectable by count. There's also a widget rendering scenario where we need to verify the end-to-end visible text output including how object-valued keys behave.

Please make sure the code is well-structured — not everything dumped into one file — and the test harness should be runnable with a single bash command. Cases live under the rcb_tests folder.