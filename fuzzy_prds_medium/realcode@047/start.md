## Product Requirement Document

Hey team, we need a small editing engine for rich-text content — basically the brain behind a formatting toolbar. Users have been complaining that when they try to bold something or turn a paragraph into a quote, nothing sticks consistently, and the floating toolbar keeps popping up in the wrong spot relative to where they've highlighted text. Super annoying UX.

The engine needs to handle toggling character-level styles (think the usual suspects), switching block structures, and managing link attachment/detachment on selected ranges. For the link stuff, remember we had that URL normalization pattern from the auth flow we built — same idea applies here, just adapt it for this context.

The toolbar positioning math should follow whatever convention we settled on in the design spec (check the spacing constants we agreed on). Output needs to be line-based key=value pairs so our test harness can compare things directly.

One big thing: the code can't be one giant file. Split it up by responsibility. The part that reads stdin and spits out stdout should be totally separate from the actual logic. Unknown or broken inputs should fail gracefully — no stack traces leaking out.

Test runner lives under rcb_tests/ and should handle multiple case directories without stomping on previous results. Can someone take a pass at this and make sure the public cases all pass?

One quick follow-up from the questions that came in: for the floating toolbar math, the top position should use a fixed gap of 14 units above the selection, so the formula is exactly offset_top = range.top - editor.top - (toolbar.height + 14). For the horizontal position, it should be centered over the selection, using offset_left = (range.left - editor.left) + (range.right - range.left) / 2 - toolbar.width / 2. Values may be fractional.

Also, on structure, this really does need to stay split cleanly by responsibility. We have four distinct core areas here: inline formatting, block formatting, hyperlink lifecycle, and toolbar geometry. Then the I/O adapter (stdin/stdout + JSON parsing) should stay as a separate thin layer from the core logic. Parsing, routing, validation, core transformation, and output formatting should each be separate concerns rather than blended together.

For link handling, if the entered address already begins with http:// or https://, it is stored unchanged. If it has no scheme, http:// is prepended before storing. For example, www.example.com becomes http://www.example.com. Same rule applies in Feature 3.1 (apply_hyperlink): prepend http:// if the address has no scheme, leave http:// or https:// addresses unchanged. See rcb_tests/public_test_cases/feature3_1_apply_link.json and the add_link command handler. And when a link gets removed, the result should report both fields exactly as url_before=<the URL that existed before removal> and entity_after=none.

One other formatting detail: if multiple inline formats are active at the same time, list them comma-separated in sorted (alphabetical) order, for example BOLD,ITALIC,UNDERLINE.