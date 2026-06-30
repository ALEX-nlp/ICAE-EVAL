## Product Requirement Document

Hey team, we need a small utility built for the framework wiring layer. Basically we keep running into silent bugs where values get swapped when injected into methods — devs aren't noticing until runtime and it's causing real pain in production. The fix is a validation + resolution tool that checks whether a method's parameters can be safely bound before anything runs, and also lets you look up exactly what name a given parameter will be bound under.

For validation: we need to catch the case where devs only half-annotate their parameters — like the auth module approach we discussed before where some params get the name-flag and others don't. That inconsistency should be a hard reject with a structured error that tells you exactly which group is broken and who's in it.

For resolution: there's a precedence rule for figuring out the final binding name — explicit marker value wins, then falls back to the param's own name, then a default. Need to handle the edge cases (blank values, missing names, etc.) cleanly.

Should be runnable from stdin/stdout with JSON commands, and there needs to be a test harness that runs all the case files automatically. Keep the core logic clean and separate from the I/O plumbing — don't want a repeat of the last module where everything was tangled together. Output format needs to be exact, cases are in the test folder.