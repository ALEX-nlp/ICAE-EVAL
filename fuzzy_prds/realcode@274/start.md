## Product Requirement Document

Hey team, we need a JSON translation utility — basically something that can round-trip JSON data in both directions. The core idea is: give it some JSON text and it spits back a structured representation of what's inside (type info, nested values, etc.), and also give it some typed value descriptors and it produces valid JSON output. We had a similar value-category inspection approach in the old data pipeline project, so use that as a reference for how we distinguish different numeric forms.

A few pain points driving this: customers keep complaining that our current tooling doesn't tell them WHY a parse failed — it just crashes with some internal exception message they can't act on. Also our serialization output is inconsistent — sometimes numbers come out wrong for certain decimal inputs, and non-finite floats like infinity or NaN just blow up instead of being handled gracefully.

We also need flexible whitespace control for the output — some consumers want compact wire format, others need something more readable. There should be like four modes or so.

One tricky bit: floating point precision needs to be configurable per-call, not globally. And the special number handling (you know, the infinity/NaN stuff) should be opt-in only — don't emit those by default.

Please make sure errors are normalized and don't leak internal runtime details. The test harness lives under rcb_tests/ so plug into that.