## Product Requirement Document

Hey team, we need to build out that input validation library we've been talking about. The idea is that instead of writing a bunch of scattered if-checks all over the place, devs can just declare what they expect from a value and get back a consistent result. Think of it like the assertion approach we used in that old form-handling module — same kind of vibe but more structured and reusable.

The engine needs to handle all the usual suspects: type checking, range/length stuff, format validation (emails, URLs, dates, that sort of thing), and some collection-level checks. There also needs to be a way to short-circuit on the first failure vs. collecting all failures at once — both patterns are needed depending on the use case.

Results should be machine-readable and stable so downstream systems can react to specific failure types without parsing human text. The codes need to be consistent across runs — can't be changing them.

Also important: the architecture can't just be one big file. We've been burned by that before. Keep the parsing, the rule logic, and the output formatting cleanly separated.

One thing I'm fuzzy on is how null values should interact with rules — like, should a null automatically fail everything, or can we make certain rules tolerant of nulls? Need to nail that down. Same question for applying a rule across a whole list of values at once. Talk to the team about the exact behaviors there.