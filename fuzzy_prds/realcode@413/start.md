## Product Requirement Document

Hey team, we need to wrap the dart_style formatter into a little adapter layer so other tools can drive it over stdin/stdout with JSON. Basically something reads a JSON blob in, calls the formatter, and spits out the result. The tricky part is we want this to feel clean — not just one giant script doing everything. Think about how we separated concerns in that old analysis pipeline we built, where the I/O layer never touched the business logic directly.

The formatter itself needs to handle whole files and also smaller snippets differently — files get a trailing newline, snippets don't. Width settings and the style version (old vs new dart style) should affect how arguments and collections get split across lines. Line endings should either follow what's already in the source or be overridable. There's also some trailing comma behavior that affects whether things stay on one line or split.

When things go wrong — bad syntax, unsafe output — we need a clean, consistent error format that doesn't leak any runtime internals like stack traces or exception class names. Also, editor-style selection range tracking needs to work, and there's a utility for splitting source into before/selected/after segments that needs proper validation.

We need a test runner script that can point at a folder of JSON case files and run all of them automatically. Make sure the whole thing is properly structured, not a god file.