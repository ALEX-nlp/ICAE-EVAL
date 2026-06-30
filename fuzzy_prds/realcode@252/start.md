## Product Requirement Document

Hey team, we need to build out that BDD step-wiring utility we talked about in the last planning session. Basically the idea is: developers write plain English scenarios and we need a tool that can hook those up to actual code. There are a few moving parts here.

First, when a step doesn't have a definition yet, the tool should spit out a ready-to-paste code stub — like, automatically handle all the annoying escaping so devs don't have to do it by hand. We had a similar escaping approach in the old regex helper module, so let's stay consistent with that.

Second, we need pattern matching that can pull out the actual argument values from a step sentence and tell you where in the string they appeared.

Third, there should be a registry where you can load up a bunch of patterns and run a step description against all of them at once.

Fourth, the tabular data attached to steps needs to be buildable in a structured way — it should blow up early if someone tries to do something invalid like adding a row before setting up columns, or mismatching the row width.

Lastly, we need tag filtering — both the "any of these" and "all of these" flavors. The AND version has some quoting syntax I can't quite remember the exact rules for, so double-check how the sub-expressions are delimited.

Please make sure the whole thing is clean and testable with no I/O side effects in the core logic.