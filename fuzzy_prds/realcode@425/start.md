## Product Requirement Document

Hey team, we need to build out that source quality analysis toolkit we've been talking about. The idea is basically a library + command adapter that devs can use to run various checks on Dart source files and get back consistent, machine-readable output. Think of it like that pipeline we wired up for the login module's validation layer — same kind of separation between the transport layer and the actual business logic.

High level: the adapter reads JSON commands from stdin, dispatches to the right core behavior, and prints results to stdout. We need support for a handful of things: converting identifier strings into different casing formats, normalizing file paths and URI inputs, parsing YAML config blobs, mapping severity labels, detecting suppression comments in source, picking the right report renderer by name, and running several source analysis rules (empty blocks, magic numbers, duplicate arguments, null assertion abuse, boolean literal comparisons, first-element access patterns, trailing commas, and throw-inside-catch).

The suppression comment thing is a bit tricky — we need both file-wide and line-local flavors, and I recall there was some case-sensitivity nuance we handled differently in the old linter prototype, so please double-check how identifiers in comments are matched.

Output format needs to be totally deterministic so the test harness can do exact string comparison. Multi-file structure is expected given the complexity here. Please make sure the core logic is not tangled up with the I/O layer.