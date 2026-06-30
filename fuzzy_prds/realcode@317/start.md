## Product Requirement Document

hey team, we need to get the fluent test toolkit shipped. basically the idea is devs are sick of writing the same low-level assert boilerplate over and over — we want something readable and expressive. i know we talked about this in the Q2 planning and there were some notes somewhere about how we handled the 'compatible check' patterns in the login module, same idea applies here for some of the type and callable stuff.

the tool should read a JSON blob from stdin, figure out what kind of check is being requested, run it, and print the result to stdout in a specific key=value line format. there are like 15 different check types — equality, ranges, truthiness, types, sizes, ordering, record lookups, text fuzzy matching, regex, containment, exception handling, value rendering, deep structural diffs, and two scenario/context lifecycle ones.

the tricky parts are: the range check has a specific boundary behavior we need to get right (users were complaining the off-by-one was causing flaky tests), the text comparison should be forgiving about whitespace and casing, and the deep comparison needs a human-readable summary when things don't match. also the context lifecycle stuff needs setup and teardown to actually wire up properly — there were some issues reported where teardown wasn't running and state was leaking between tests.

please make sure the output format is exactly right, some CI pipelines are parsing it directly. multi-file layout preferred, keep things clean.