## Product Requirement Document

Hey team, we need to build out this native bridge adapter thing for the Neon bindings project. Basically the idea is that native Rust code should be able to hand values back and forth with JavaScript without developers having to write all that ugly glue code every single time. Think of it like that interop layer we did for the login module — same vibe but for the full value spectrum: numbers, strings, arrays, objects, buffers, dates, errors, async stuff, all of it.

The way it works is commands come in as JSON on stdin and the results go to stdout in a key=value line format. Each command has an operation and a scenario field at minimum, sometimes extra fields depending on what's being tested. The adapter needs to handle all the primitive types, binary memory views, boxed stateful objects, async callbacks and promises, and error categories without leaking internal Rust exception names to the caller.

One thing that tripped us up last time is that error categories need to be normalized — callers should never see raw implementation names. Same goes for script evaluation failures, there are two different failure modes there that need to be reported differently.

Also the binary memory stuff has some tricky overlap/borrow behavior that needs to fail gracefully. Users have been complaining about crashes at the boundary when they try to do concurrent reads and writes on the same buffer region, so that needs to be locked down properly.

Please follow the same patterns from the existing test fixtures in rcb_tests.

One quick follow-up from the questions that came in: for the key=value stdout format, Undefined must be rendered as the literal string 'undefined' and null as the literal string 'null'. We should not use empty strings, 'None', or any other representation. The expected shape there is exactly 'undefined=undefined\nnull=null\n'.

Also want to make the script eval behavior extra explicit since that was a source of confusion. There are exactly two distinct failure modes for script evaluation. A runtime exception thrown during execution must be reported as 'error=script_exception' followed by a 'message=<text>' line. A parse/syntax failure must be reported as 'error=script_syntax' with NO message line and must NOT leak any runtime exception class names. More broadly, error categories need to stay normalized to the stable labels 'generic_error', 'type_error', and 'range_error', and we should never expose Rust or internal exception type names. Type and range errors must additionally print 'base_error=true'. That same normalized contract is what we should use for memory-region problems too, so invalid memory region accesses and overlapping mutable borrow attempts fail gracefully in output instead of panicking or crashing, with things like 'range_error' for out-of-bounds regions.

For async, the important bit is that the adapter has to wait. In the 'lazy_add' async scenario the output must be 'result=3\n'. Async callbacks and promises must resolve before the adapter writes output, so the adapter must await resolution. If they reject, that should still come back through the same normalized error category contract.

And for boxed values, both 'greet' and 'ref_greet' need to produce identical observable output: 'name=<name>\ngreeting=Hello, <name>!\n'. The only difference is that 'ref_greet' uses a borrowed reference rather than ownership transfer, but callers should see the same thing either way. If there’s a borrow/type check failure there, that should also use the normalized error categories.

Last thing, just reaffirming the separation we talked about in the architecture notes: the JSON I/O adapter should stay decoupled from the core domain logic, following the same adapter-pattern split we already called out. That keeps the stdin/stdout protocol handling from getting tangled up with the actual value conversion and behavior.