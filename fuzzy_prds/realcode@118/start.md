## Product Requirement Document

Hey team, we need to wrap up the local storage abstraction library before the sprint ends. The basic idea is that we want developers to be able to stash stuff like user preferences, session tokens, and app config objects without having to manually handle serialization every single time. Think of it like that settings persistence layer we built for the onboarding flow — same vibe but more generalized and reusable across products.

A few things that came up in the last retro: some legacy data in the wild isn't cleanly formatted, so we need to make sure reads don't blow up on that. Also the ops team wants to be able to hook into writes to do auditing — and apparently they sometimes need to be able to block a write from going through entirely, so there needs to be some kind of intercept mechanism.

We also got a complaint that storing empty or blank keys causes silent weirdness downstream, so that needs to be handled properly with a clear error signal. Same deal for trying to store a null raw string — that should also fail loudly with something descriptive.

Should support both sync and async call styles since different parts of the platform use different patterns. The underlying storage backend should be swappable so QA can test without touching real browser storage. Make sure the design doesn't end up as one giant file — separate concerns cleanly.