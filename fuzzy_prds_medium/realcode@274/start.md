## Product Requirement Document

Hey team, we need a JSON translation utility — basically something that can round-trip JSON data in both directions. The core idea is: give it some JSON text and it spits back a structured representation of what's inside (type info, nested values, etc.), and also give it some typed value descriptors and it produces valid JSON output. We had a similar value-category inspection approach in the old data pipeline project, so use that as a reference for how we distinguish different numeric forms.

A few pain points driving this: customers keep complaining that our current tooling doesn't tell them WHY a parse failed — it just crashes with some internal exception message they can't act on. Also our serialization output is inconsistent — sometimes numbers come out wrong for certain decimal inputs, and non-finite floats like infinity or NaN just blow up instead of being handled gracefully.

We also need flexible whitespace control for the output — some consumers want compact wire format, others need something more readable. There should be like four modes or so.

One tricky bit: floating point precision needs to be configurable per-call, not globally. And the special number handling (you know, the infinity/NaN stuff) should be opt-in only — don't emit those by default.

Please make sure errors are normalized and don't leak internal runtime details. The test harness lives under rcb_tests/ so plug into that.

One small follow-up from the questions that came in: when we render the parsed structure, the shape needs to be very literal and stable. Objects should come out as `object{key=value|...}` with pipe separators between members, arrays as `array[value|...]`, strings as `string:<text>`, booleans as `boolean:true` or `boolean:false`, null as `null`, and numbers should always carry their category prefix like `unsigned_integer:1` or `number:2.004`. If things are nested, we keep the whole tree intact in that same format all the way down.

On the JSON input side, Unicode escapes like `\u00ff` should be decoded to the actual character internally, but if we render that back out to stdout then anything outside printable ASCII needs to be emitted again as `\uXXXX` using lowercase hex. Also, if the input had `\/`, that should just render as a literal `/` in the output.

Also confirming the number buckets since a couple folks asked: positive integers, including arbitrarily large ones, are `unsigned_integer`. Negative integers are `signed_integer`. Anything with a decimal point or exponent notation is `number`. Booleans are `boolean` and null is `null`. That numeric type classification logic from feature3 (feature3_parse_numbers_and_scalars.json) is the core category system we want in the parser domain layer.

For parse errors, we need to be strict here: every parse failure must print exactly `ok=false\nerror=parse_error\n` to stdout. No language-specific exception names, no stack traces, and no internal parser diagnostics. The error category is always the normalized token `parse_error`.

On the serialization side, the adapter should read a JSON object with a `kind` field and a `value` field. The `kind` examples are `"null"`, `"string"`, `"list"`, `"map"`, `"double"`, and `"special"`, and the `value` type depends on the kind. For maps, the value is a JSON object mapping string keys to nested kind/value descriptors. For lists, the value is a JSON array of descriptors. For double and special kinds, the value is a string representation of the number.