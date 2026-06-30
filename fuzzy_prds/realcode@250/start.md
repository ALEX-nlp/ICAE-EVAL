## Product Requirement Document

Hey team, we need a small parser library for the Java test runner output. Basically the VS Code Java test extension streams these weird percent-prefixed lines when it runs JUnit tests, and right now every team that wants to show results in their editor has to re-parse this themselves and they all get it wrong. We want a single library that eats that raw stream and spits out clean structured signals so the editor knows when a test started, whether it passed or blew up, etc.

For failures/errors the trace should be rendered so developers can click into the exact file and line — similar to how we handled the deep-link formatting in that login module diagnostic thing we did a while back, so just follow the same pattern there.

The tricky part is anchoring the failure message to the right source line. When a test throws from deep inside helper methods, we want the squiggle to land on the right spot in the test file, not some random library frame. We've had bug reports about this from a few teams already.

Also please make sure the whole thing is testable end-to-end with a shell script so QA can just run one command. The adapter that talks to stdin/stdout should be kept separate from the core parsing logic. Don't mix those concerns. The line numbering in the output needs to match what the editor expects or the jump-to-source feature breaks.