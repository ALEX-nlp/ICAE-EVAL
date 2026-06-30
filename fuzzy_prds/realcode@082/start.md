## Product Requirement Document

Hey team, we need to build that field-level data protection layer we've been talking about for a while. The core idea is that developers should be able to mark certain model fields as sensitive (think emails, SSNs, credit card numbers) and the system should just handle keeping that data safe in storage automatically — no manual crypto code at the call site. It should feel like a normal attribute to the developer but store something unreadable in the backing column.

We also need it to be smart about edge cases — empty values, missing values, that sort of thing — and support the same kind of conditional logic we used on the login module last time. There should also be a way to swap in a custom encryption backend for teams that have their own crypto setup.

Inheritance needs to work correctly too — child models should pick up whatever the parent declared. And we need class-level helpers for doing the transform outside of an instance context.

Please make sure the codebase isn't just one big file — this thing has enough moving parts that it needs to be split up properly. The runner/adapter that processes the test harness commands should live separately from the core logic, which should know nothing about JSON or stdin.

Let me know if anything's unclear, but try to dig into the existing test cases first before pinging me.