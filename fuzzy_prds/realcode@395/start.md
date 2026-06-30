## Product Requirement Document

Hey team, we need to build out that database adapter layer we've been talking about. Basically developers are spending way too much time writing boilerplate to talk to our distributed SQL backend — things like manually constructing requests, figuring out schema stuff, and keeping track of transaction state. It's causing a ton of bugs and wasted engineering time.

The adapter needs to handle the full lifecycle: connecting to databases, running queries and schema changes, managing transactions without leaking internal errors to callers, and doing all the ORM-style read/write mapping. We also need it to handle the metadata introspection stuff the same way we did for that session/service mock layer — you know, the approach we used for the gRPC service simulation.

One big thing: schema changes should be batchable so we don't end up with partial migrations. And the column type system needs to handle the variable-length vs fixed-length distinction correctly, especially when no size is specified — refer to how the existing type formatting logic works in the schema module.

Also we need the SQL literal decoding to cover all the quoting styles people actually use in practice. The transaction error handling should surface clean category names rather than raw exceptions. Make sure the whole thing is properly structured — no giant single files please. Should be production-grade layout.