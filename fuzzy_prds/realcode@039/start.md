## Product Requirement Document

Hey team, we need a small text utility library — basically something that cleans up indented blocks of text that developers embed inside already-indented code. The core idea is: when you write a multi-line string inside a function or class, all those lines pick up the surrounding indentation, and we want to strip that shared prefix out automatically so the output is clean and left-aligned. Relative indentation between lines should stay intact though — if one line is deeper than another, it should stay that way after processing.

We also need this to work on raw binary buffers, not just decoded strings, similar to how we handled the binary path in that old encoding module. And there's a Windows line-ending thing — if the content uses CRLF, those carriage returns need to survive the transformation.

A few edge cases I know about: blank lines and whitespace-only lines should be handled gracefully (they shouldn't blow things up or count toward the indent calculation). Also there's something about the first line being special — I think if the block starts immediately on the first line vs. starting after a line break changes the behavior slightly, but I'm fuzzy on the exact rule there.

Need a CLI adapter for testing, plus an automated test harness that runs JSON-based test cases. Keep the core logic separate from the I/O stuff please.