## Product Requirement Document

Hey team, we need to build out that BDD step-wiring utility we talked about in the last planning session. Basically the idea is: developers write plain English scenarios and we need a tool that can hook those up to actual code. There are a few moving parts here.

First, when a step doesn't have a definition yet, the tool should spit out a ready-to-paste code stub — like, automatically handle all the annoying escaping so devs don't have to do it by hand. We had a similar escaping approach in the old regex helper module, so let's stay consistent with that.

Second, we need pattern matching that can pull out the actual argument values from a step sentence and tell you where in the string they appeared.

Third, there should be a registry where you can load up a bunch of patterns and run a step description against all of them at once.

Fourth, the tabular data attached to steps needs to be buildable in a structured way — it should blow up early if someone tries to do something invalid like adding a row before setting up columns, or mismatching the row width.

Lastly, we need tag filtering — both the "any of these" and "all of these" flavors. The AND version has some quoting syntax I can't quite remember the exact rules for, so double-check how the sub-expressions are delimited.

Please make sure the whole thing is clean and testable with no I/O side effects in the core logic.

A couple follow-ups from the questions that came in. On the escaping piece, the regex escaping is only for these characters: `|`, `(`, `)`, `[`, `]`, `{`, `}`, `^`, `$`, `*`, `+`, `?`, `.`, and `\`. Everything else should pass through unchanged. And for snippet generation, it’s definitely a two-step thing on the step text: first escape every regex metacharacter so it matches literally, then take that already-escaped result and escape every double-quote and every backslash again so it’s safe inside a double-quoted C-style string literal. After that, wrap the whole thing with `^` and `$`. Same two-pass behavior should stay consistent anywhere we’re doing that snippet-style escaping flow.

Also, the generated stub shape should be exact. The keyword is uppercased, and the first line should look like `THEN("^...$") {`. After that it’s a newline, then four spaces followed by `pending();`, then a newline, then a closing brace `}`, then a final newline. So the body is exactly that formatting, not just roughly similar.

For `regex_find_all`, scanning should be consecutive and non-overlapping starting from the beginning of the string. We only report the first capturing group from each token match. The first output line is `matched=true` if we found at least one token, otherwise `matched=false`. Then the token values come out as `token[0]=...`, `token[1]=...` and so on. On positions, the `position` for each captured group is the zero-based character offset in the full input string, not relative to the match start and not relative to any other group. Groups start at 0 and should be reported in pattern order.

One other important boundary line: the core business logic needs zero dependency on stdin/stdout or JSON parsing. The execution adapter layer is the only thing that should read JSON commands from stdin, turn those into method calls on the core domain objects, and write formatted results to stdout. Core domain stays fully testable with no I/O.

And on the AND tag syntax I was fuzzy about earlier, the format is the one where each sub-expression is wrapped in double-quotes and separated by commas, like `"@a,@b", "@c", "@d,@e,@f"`.