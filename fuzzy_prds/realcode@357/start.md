## Product Requirement Document

Hey team, we need to build out that symbolic expression toolkit we've been talking about. The main thing is we need a way to take these parenthesized prefix-style expressions and do something useful with them — read them, normalize the identifiers, evaluate the math/logic stuff, and print the results back out in a way that can be re-read. 

The identifier normalization piece is important — we had that issue last time where names with dashes and question marks and weird unicode symbols were breaking things in host runtimes. The fix we landed on for the login module's identifier escaping should inform this — basically we need a reversible encoding scheme, same family of ideas.

For the reader, it needs to handle the usual collection types (round parens, square brackets, curly braces, and that set syntax with the hash), plus a discard/skip marker thing. Errors need to come back in a normalized format, not just blow up.

The evaluator should cover arithmetic, comparisons, bitwise ops, and membership/indexing. Some operators behave differently depending on how many arguments you give them — that needs to be handled gracefully rather than crashing.

Output formatting needs to round-trip cleanly, including some standard library types. Everything should be separated into sensible modules — no giant single-file mess please. The interface is JSON in/out over stdin/stdout.