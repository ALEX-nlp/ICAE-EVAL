## Product Requirement Document

Hey team, we need to build out that input validation library we've been talking about. The idea is that instead of writing a bunch of scattered if-checks all over the place, devs can just declare what they expect from a value and get back a consistent result. Think of it like the assertion approach we used in that old form-handling module — same kind of vibe but more structured and reusable.

The engine needs to handle all the usual suspects: type checking, range/length stuff, format validation (emails, URLs, dates, that sort of thing), and some collection-level checks. There also needs to be a way to short-circuit on the first failure vs. collecting all failures at once — both patterns are needed depending on the use case.

Results should be machine-readable and stable so downstream systems can react to specific failure types without parsing human text. The codes need to be consistent across runs — can't be changing them.

Also important: the architecture can't just be one big file. We've been burned by that before. Keep the parsing, the rule logic, and the output formatting cleanly separated.

One thing I'm fuzzy on is how null values should interact with rules — like, should a null automatically fail everything, or can we make certain rules tolerant of nulls? Need to nail that down. Same question for applying a rule across a whole list of values at once. Talk to the team about the exact behaviors there.

A couple more specifics from the team convo so we lock this down cleanly. The violation codes are not just generally stable, they are fixed and must never change. The exact mapping is: float=9, integer=10, digit=11, integerish=12, boolean=13, not_empty=14, not_null=15, string=16, regex=17, min_length=18, max_length=19, starts_with=20, contains=21, in_choices=22, numeric=23, is_array=24, null=25, key_exists=26, not_blank=27, uuid (no alias)=40, range=30, alnum=31, is_true=32, equal=33, same=34, min=35, max=36, length=37, is_false=38, ends_with=39, not_equal=42, not_same=43, not_in_choices=47, email=201, url=203, empty=205, json_string=206, scalar=209, less_than=210, less_or_equal=211, greater_than=212, greater_or_equal=213, date=214, key_not_exists=216.

On the null question, we do have a definite behavior now: when the request carries `null_or: true` alongside a check, the engine must short-circuit to valid immediately if the value is null, without invoking the underlying rule at all. Only non-null values are forwarded to the rule for evaluation. This applies to any rule and should be handled as wrapper behavior in the adapter/dispatch layer, not inside individual rules.

Also worth being explicit about the comparison rules because people asked. `equal` (code=33) performs a type-coercing comparison, so string `"10"` equals integer `10`. `same` (code=34) requires both value and type to match strictly. In the same spirit, `not_equal` (code=42) fails when values are loosely equal, and `not_same` (code=43) fails when values are strictly identical.

For collection handling, when the request carries `all: true`, the value is expected to be a collection (array). The named rule is applied to each element in order. The check stops at the first element that fails and returns that element's violation, using the same code and message format as a single-value check. If all elements pass, the result is valid.

For `chain` mode, the request supplies a `value` and a `steps` array where each step is `{check, args}`. Steps are evaluated left to right against the same value. Execution halts at the first failing step and returns that violation. If all steps pass, the result is valid. And if a step references a rule name that does not exist, the output must be exactly two lines: `error=unknown_assertion` followed by `message=Assertion "<ruleName>" does not exist.`

On structure, keeping this split up is a hard requirement, not just a preference. We need (1) a core engine module containing rule definitions and a ViolationError type with code+message, fully decoupled from stdin/stdout/JSON, (2) a rule registry for resolving rule names to implementations, (3) an I/O adapter that reads JSON from stdin, routes to the engine, and renders the stdout contract, and (4) an output formatter. New rules must be addable without modifying existing rule files, so we should stick to the Open/Closed Principle here.

Last thing, this should follow the declarative rule-based check/chain/lazy dispatch pattern described in the Input/Output Contract section of start.md, specifically the three execution modes and their JSON request schemas, and that includes the `null_or: true` flag on a check-mode request which makes any rule skip evaluation and return valid when value is null.