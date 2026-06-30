## Product Requirement Document

Hey team, we need to get this retry control utility shipped. The basic idea is that we want developers to stop copy-pasting retry loops everywhere and instead use a clean policy-based approach. Think of it like that circuit-breaker pattern we discussed last quarter but simpler — just configurable retries with timing.

Some things I know we need: different wait strategies (the usual suspects — flat wait, growing wait, the math sequence one), a way to say 'retry on any error except these specific ones' with proper parent/child error awareness, and lifecycle hooks so callers can observe what's happening. We also need async support — the team mentioned needing both a default thread pool and the ability to bring your own.

One thing that came up in the last sprint review: users were frustrated that certain return values weren't being treated as failures — like when the downstream service returns a 'not ready yet' signal instead of throwing. We need to handle that.

Also, validation should be strict — people were shipping bad configs silently and only finding out at runtime. Should catch things like missing timing config, contradictory retry rules, etc.

Refer to how we handled the exception hierarchy in the exclusion matching work — same inheritance-aware logic should apply here. Custom predicate support would be a bonus if it's not too much lift.

Target language is Java. Keep it clean and testable.