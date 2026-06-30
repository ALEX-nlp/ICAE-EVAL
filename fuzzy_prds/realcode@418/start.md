## Product Requirement Document

Hey team, we need to build out this scenario runner tool we've been talking about. Basically it should let devs write plain English test specs and have the system run them and tell you what passed, what broke, what's not done yet, etc. Think of it like that BDD thing we were experimenting with last quarter — same general vibe.

A few things I know we need: it should handle shared setup blocks that run before each test, support table-driven tests where one template runs multiple times with different data, and let people filter which tests to run by labels or by name or even by pointing at a specific line in a file. Oh and there's some kind of safety valve where if a label is overused (more than a set number of times) the whole run should stop with a clear error before anything even executes.

There's also a mode where nothing actually runs but you still get the report (useful for sanity checking), a strict mode where incomplete steps count as failures, and a command that suggests code stubs for steps that don't have implementations yet. We also need the keyword lookup thing for different languages — the team mentioned something about reusing the approach from the i18n module we did before.

Please make sure the codebase is split into sensible modules, not one giant file. The JSON test harness should be a thin wrapper, not mixed into the core logic.