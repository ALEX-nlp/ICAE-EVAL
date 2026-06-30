## Product Requirement Document

Hey team, we need a small editing engine for rich-text content — basically the brain behind a formatting toolbar. Users have been complaining that when they try to bold something or turn a paragraph into a quote, nothing sticks consistently, and the floating toolbar keeps popping up in the wrong spot relative to where they've highlighted text. Super annoying UX.

The engine needs to handle toggling character-level styles (think the usual suspects), switching block structures, and managing link attachment/detachment on selected ranges. For the link stuff, remember we had that URL normalization pattern from the auth flow we built — same idea applies here, just adapt it for this context.

The toolbar positioning math should follow whatever convention we settled on in the design spec (check the spacing constants we agreed on). Output needs to be line-based key=value pairs so our test harness can compare things directly.

One big thing: the code can't be one giant file. Split it up by responsibility. The part that reads stdin and spits out stdout should be totally separate from the actual logic. Unknown or broken inputs should fail gracefully — no stack traces leaking out.

Test runner lives under rcb_tests/ and should handle multiple case directories without stomping on previous results. Can someone take a pass at this and make sure the public cases all pass?