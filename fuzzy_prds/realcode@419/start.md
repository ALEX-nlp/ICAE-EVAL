## Product Requirement Document

Hey team, we need to wrap up the numerical toolkit library we've been building. Most of the core math pieces are done but we need to make sure the whole thing is wired up properly end-to-end so someone can actually run it. The execution layer needs to read JSON from stdin, route each command to the right piece of logic, and write the result back out — basically the same pattern we used on the recommendation service adapter last quarter, so follow that same separation philosophy.

A few things I keep hearing from devs who tried early builds: error messages are leaking internal stack traces which is a no-go for any external-facing tool, and some of the numeric output has inconsistent decimal formatting (trailing zeros showing up in some places, missing in others). Also the matrix printing for multi-output operations needs to be consistent — comma-separated on one line per row.

One thing that came up in last week's sync: the KD-tree query feature needs to support at least three distance strategies and two splitting approaches — make sure those are all hooked up. Similarly the learning rate schedules each have their own formula so don't accidentally collapse them into one generic thing.

The whole thing should be organized into separate files by concern — no monoliths. Each feature family gets its own module. Adapter stays separate from math logic. If something is invalid input, return a clean category-based error string, nothing else.