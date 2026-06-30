## Product Requirement Document

Hey team, we need to build that in-memory filesystem thing we talked about in the last planning session. Basically developers are super frustrated with tests that write to real disk — things are slow, there's leftover temp garbage everywhere, and some of the weirder edge cases (you know, the loop stuff, the empty-vs-not-empty situations) are basically impossible to reproduce reliably on CI. We want a clean engine that lives entirely in memory so tests are fast and deterministic.

The engine needs to handle all the usual suspects: directories (create, list, delete, move, navigate), files (read/write in different modes, copy, rename, measure size), symbolic links, and seekable file handles. It should behave like a real POSIX filesystem would, including the error categories — we want those normalized the same way we did for the error handling in that storage abstraction layer from the config module.

Important: this can't be one giant file. Split it up properly, separate the I/O adapter from the actual logic. The adapter reads a JSON program from stdin and writes results line by line to stdout. Refer to how we structured the path resolution piece in the existing navigation utilities — same separation idea applies here.

There are a few tricky bits around temp directory naming, how trailing newlines behave on line reads, and what happens when you follow a link that loops back on itself. Make sure those are handled correctly.