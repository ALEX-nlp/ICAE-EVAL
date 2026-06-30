## Product Requirement Document

Hey team, we need a DOM assertion helper tool — basically a small utility that takes a JSON command over stdin and spits out a JSON result to stdout. The idea is that our QA folks are drowning in repetitive DOM inspection boilerplate and we want to give them a clean contract-based interface instead. Think of it like that adapter pattern we used on the login module last time — same separation idea, where the I/O layer just translates commands into calls to the real logic underneath.

The tool needs to handle things like: checking if elements exist (or don't), verifying text content (exact or fuzzy), inspecting attributes and their values, checking CSS classes, looking at form control values, and also disabled/focus states. Oh and there's some whitespace normalization thing we need — users keep complaining that copy-pasted text comparisons break because of invisible formatting differences.

For errors — if someone passes a weird target type that we don't understand, we need a normalized error response rather than a crash. The output format needs to be consistent and pretty-printed.

Also the whole thing should be structured properly, not just one giant file — our new engineer complained last time about god files. Reference the existing test contracts in the rcb_tests folder if you need to understand the expected shapes. Let me know if anything is unclear, I'm not super technical on the DOM side.