## Product Requirement Document

Hey team, we need to build that database read-routing thing we've been talking about for ages. The basic idea is: we have primary and replica DB nodes, and right now everything hits the primary which is getting hammered. We want a way to wrap chunks of code so reads inside that wrapper go to the replica instead. Pretty similar to how we handled the connection-scoping stuff in the old session middleware, if you remember that pattern.

There should also be a global 'just distribute everything by default' toggle for apps that want to go all-in. Key thing though — after someone does a write, we can't serve their next read from a stale replica, that's caused support tickets before.

We also need some kind of staleness protection — if the replica is too far behind, we should either blow up loudly or quietly fall back to primary depending on config. Same deal if there are no replicas at all. Background jobs should also play nicely with this.

One thing I keep forgetting to mention: there's a lazy query issue where people return unexecuted query objects from the wrapper and then wonder why the replica isn't being used — we should warn about that.

Edge cases like calling the wrapper without actually passing it a block of work, or passing in option keys we don't recognize, should produce clear errors. Let me know if anything's unclear, I'll be around.

One quick follow-up with the extra specifics people asked for. If the distribution entry point gets called without a block, it should raise the missing-block case and the output needs to be exactly two lines: `error=missing_block` and then `message=Missing block`. Same idea for bad option keys: if someone opens the distribution scope with keys we don’t recognize, raise the unknown-keywords case and return `error=unknown_keywords` followed by `message=Unknown keywords: <key1>, <key2>`, with the offending keys listed in the same order they were passed in.

On routing behavior, a scope opened with `replica: true` should send reads in that scope to the replica even if default-distribution mode is off, and reads outside that scope should still use the primary. Also, SQL comment prefixes, meaning the `prefix` field on a read op, should not influence routing at all. On the flip side, when default-distribution mode is on, a scope opened with `primary: true` should override that default and keep all reads in that scope on the primary.

For lag reporting, the `replication_lag` operation should return the current replica lag as a numeric value and render it as `replication_lag=<value>`, for example `replication_lag=2`.

One subtle but important bit on the stale-read protection: in default-distribution mode (`by_default: true`), if a write happens outside any explicit scope, then every later top-level read needs to stay pinned to the primary, not the replica. But inside an explicit distribution scope, a write does not pin later reads in that same scope; those reads still go to the replica. Then when that scope ends, any write that happened before the scope was entered starts mattering again for top-level reads.

Also, any read inside a transaction block must always go to the primary, even if that transaction is nested inside a distribution scope. Transactional work needs to stay on the writable node. And to make all of this work consistently, we do need the distribution scope/context-state piece that keeps track of whether a scope is active, whether a write has happened, and whether a transaction is currently open, basically the same kind of thread-local or stack-style context tracking we’ve used before in the core domain.