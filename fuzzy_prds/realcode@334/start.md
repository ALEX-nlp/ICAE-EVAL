## Product Requirement Document

Hey team, we need to build out this native bridge adapter thing for the Neon bindings project. Basically the idea is that native Rust code should be able to hand values back and forth with JavaScript without developers having to write all that ugly glue code every single time. Think of it like that interop layer we did for the login module — same vibe but for the full value spectrum: numbers, strings, arrays, objects, buffers, dates, errors, async stuff, all of it.

The way it works is commands come in as JSON on stdin and the results go to stdout in a key=value line format. Each command has an operation and a scenario field at minimum, sometimes extra fields depending on what's being tested. The adapter needs to handle all the primitive types, binary memory views, boxed stateful objects, async callbacks and promises, and error categories without leaking internal Rust exception names to the caller.

One thing that tripped us up last time is that error categories need to be normalized — callers should never see raw implementation names. Same goes for script evaluation failures, there are two different failure modes there that need to be reported differently.

Also the binary memory stuff has some tricky overlap/borrow behavior that needs to fail gracefully. Users have been complaining about crashes at the boundary when they try to do concurrent reads and writes on the same buffer region, so that needs to be locked down properly.

Please follow the same patterns from the existing test fixtures in rcb_tests.