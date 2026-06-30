## Product Requirement Document

Hey team, we need to build out this mobile ads adapter layer that sits between our app code and the native ad SDKs. Basically right now every team that wants to show ads has to write all this boilerplate to talk to the platform channel, handle the async callbacks, track which ad is which, etc. It's a mess and every squad is doing it differently.

The adapter should handle the full lifecycle — setting up targeting preferences (think privacy stuff, content ratings, test devices), kicking off the SDK init and reporting back what adapters came up, loading different ad formats with their own flavors of request data, and then dispatching the right callbacks when platform events come back in.

One thing that came up in the Android vs iOS review — remember how we handled that unit normalization issue in the analytics pipeline last quarter? We need something similar here for the timing values that come back from the two platforms, they're in different units and need to be reconciled before surfacing to callers.

Also the inline ad widgets have that double-mount footgun we've seen cause crashes in production — we need the adapter to guard against that cleanly without blowing up the host runtime.

For the gateway codec piece, make sure all the structured types (requests, sizes, errors, reward payloads) survive a round-trip cleanly. The ad registry needs to hand out stable numeric IDs starting from zero and keep track of what's loaded. Full-screen ads that aren't loaded yet should fail gracefully. Ping me if the scope is unclear.