## Product Requirement Document

Hey team, we need a BSON toolkit library that lets devs work with binary JSON stuff without having to hand-roll all the encoding/decoding themselves. Basically the pain point is that every team that touches MongoDB data ends up writing their own brittle conversion code and then things break at the edges — weird number widths, dates that lose precision, identifiers that don't round-trip cleanly, that kind of thing.

The tool should be runnable from the command line where you pipe in a JSON command and get back predictable text output. Think of it like that encoding helper we built for the auth service — same idea but for BSON types. It needs to handle the two flavors of Extended JSON (you know, the strict one and the looser one), plus wire-format encode/decode for whole documents, looking up nested fields by path, object IDs, dates, the high-precision decimal type, binary blobs with subtype metadata, and regex+timestamp combos.

Errors should be consistent — don't just throw, normalize them into something the downstream consumer can pattern-match on. Output format needs to be deterministic line-by-line, not just a blob.

Also the codebase structure matters here — don't just dump everything in one file, keep the CLI adapter separate from the actual domain logic. We've had bugs before where test output formatting leaked into core business logic.

Let me know if the scope is unclear on any of the type-specific behaviors.