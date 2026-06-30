## Product Requirement Document

Hey team, we need to build that database read-routing thing we've been talking about for ages. The basic idea is: we have primary and replica DB nodes, and right now everything hits the primary which is getting hammered. We want a way to wrap chunks of code so reads inside that wrapper go to the replica instead. Pretty similar to how we handled the connection-scoping stuff in the old session middleware, if you remember that pattern.

There should also be a global 'just distribute everything by default' toggle for apps that want to go all-in. Key thing though — after someone does a write, we can't serve their next read from a stale replica, that's caused support tickets before.

We also need some kind of staleness protection — if the replica is too far behind, we should either blow up loudly or quietly fall back to primary depending on config. Same deal if there are no replicas at all. Background jobs should also play nicely with this.

One thing I keep forgetting to mention: there's a lazy query issue where people return unexecuted query objects from the wrapper and then wonder why the replica isn't being used — we should warn about that.

Edge cases like calling the wrapper without actually passing it a block of work, or passing in option keys we don't recognize, should produce clear errors. Let me know if anything's unclear, I'll be around.