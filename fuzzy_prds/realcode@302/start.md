## Product Requirement Document

hey team, we need a small runtime value inspection utility in Node.js. basically the idea is: given any JS value, we want a single consistent way to ask 'what is this thing?' and 'what does it look like when you squish it into a bool/number/string?' and also 'can you make this an object for me?'. right now every team that touches a dynamic payload is rolling their own typeof ladder and they keep getting different answers for edge cases — like one service thinks an empty array is truthy-ish numeric zero and another forgets that typed arrays are also objects, it's a mess.

the entry point should read a JSON command off stdin and print results line by line. the value description format is kind of like what we did for the sandbox descriptor protocol in that auth boundary work — same neutral tagging idea, just applied here.

for the object categories, remember the 'object' bucket should be broad — things like arrays, buffers, functions, promises all count. null does NOT. and functions are special in two ways simultaneously.

for boxing, primitives get wrapped fresh (no same reference), everything else comes back as-is. we also need a test runner script under rcb_tests/ that saves raw stdout per case into namespaced files.

please keep the classifier, coercion logic, and I/O adapter in separate logical units — no god files. errors should never bubble raw exceptions to stdout.