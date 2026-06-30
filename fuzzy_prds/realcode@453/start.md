## Product Requirement Document

Hey team, we need to build out this data interchange toolkit thing that our distributed compute pipeline depends on. Basically it's a small library that can handle a bunch of low-level operations — think moving data around, running user logic on rows, that kind of stuff. The whole thing needs to be driven by a single stdin/stdout interface (JSON in, text out), similar to what we did with the serialization layer on the analytics project last quarter.

The big thing is reliability and determinism — every run with the same input must produce the exact same output, no surprises. Error reporting is super important too; we can't be leaking runtime-specific stuff like exception class names or stack traces — needs to be a small, stable set of neutral categories that works across different language runtimes.

We need support for things like comparing integer sequences, converting values between types, wire-level serialization of primitives, round-tripping objects (including some polymorphism scenarios), parsing type schemas, timestamps with sub-second precision, row-level typed access, composable user functions, transformation serialization, and dependency metadata records with file persistence and sortable naming.

For output formatting, booleans, numbers, and collections all have specific rules we need to nail down — check how we handled the rendering rules in the previous reporting module for reference. The sentinel value behavior for byte block reads is also a bit quirky so make sure whoever picks this up digs into the spec carefully.