## Product Requirement Document

Hey team, we need to build out that test linting library we've been talking about. Basically the idea is that devs paste in their test source code and a config of which checks they want enabled, and the tool spits out a structured report of problems. Think of it like the same pattern we used for the import validator we shipped last quarter — same kind of adapter wrapping the core logic.

The output needs to be consistent and machine-readable so CI pipelines can consume it. Each problem should say which rule fired, a human-readable message, where in the file it is (line and column), and how bad it is. Some checks also need to support auto-fixing, where the tool emits the corrected source alongside the diagnostics.

We also need to handle that weird snapshot preprocessing flow — someone on the test infra team said there's a two-phase thing where you preprocess a snapshot file and then postprocess a message array to filter it down. That part is a bit fuzzy to me honestly, just make sure it works like the existing snapshot tooling expects.

The checks we need cover things like accidentally committed skip/focus flags, tests with no real assertions, broken async assertion patterns, bad test titles, messy hook setup, wrong import patterns, and a few more. The rules should be individually toggleable. Severity should map to numbers the way our other linting tools do it. Please keep the core logic totally separate from how input/output is handled.