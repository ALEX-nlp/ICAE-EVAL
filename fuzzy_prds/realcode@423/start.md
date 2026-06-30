## Product Requirement Document

Hey team, we need a text templating engine built in Rust (the cobalt-org/liquid-rust project). Basically it should take a template string plus some data and spit out a rendered string. Think of it like how we do the email rendering pipeline — similar idea to what we wired up for the config-gen tool last quarter, just more general purpose.

The engine needs to handle variable substitution (including nested object access), a bunch of built-in filters for strings, numbers, collections, and HTML escaping, control flow like if/else and for loops, variable assignment and capture blocks, whitespace trimming controls, and partial template inclusion. Filters should be chainable with pipe syntax and support arguments.

One thing that's been a real headache with our current approach: bad templates silently produce garbage output or just crash at runtime with no useful signal. We need the new engine to distinguish between a template that's broken at the structure level versus one that fails because the data isn't what we expected — and report those separately so our ops team can triage without digging through stack traces.

The adapter layer should read a JSON blob from stdin and write the result to stdout. If something goes wrong it should print one of those neutral error codes we discussed (refer to the error handling convention we settled on in the parse/render split discussion). Architecture needs to be multi-file, clean separation of concerns — not a single god file. SOLID principles, extensible filter and tag registry, the usual.