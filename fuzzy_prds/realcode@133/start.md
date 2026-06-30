## Product Requirement Document

Hey team, we need to sort out the feature flag system for the web app. Basically right now devs are copy-pasting if/else checks all over the place — in views, templates, URL configs — and every time we want to roll something out to a subset of users or kill a feature during an incident we have to do a full deploy. It's a mess and things keep drifting out of sync between layers.

We need a clean, centralized way to toggle behaviors on/off at runtime without touching code. Flags should be evaluatable against things like the current user, URL path, query params, date/time, and so on — similar to how we handled the conditional login stuff last sprint, but more generalized. The system should work across views, URL routing, and templates consistently.

There should also be a way to pull flag definitions from multiple places — both static config and whatever storage backend we're using — and merge them. Validation, admin forms, caching per request, all of that needs to be covered. If a flag isn't defined at all, that should be distinguishable from a flag that's explicitly turned off — that distinction has burned us before.

Also the code structure matters here, this shouldn't end up as one giant file. Keep things separated by responsibility. Let's make sure edge cases like missing context, bad config, and broken providers are handled gracefully and don't just blow up.