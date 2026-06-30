## Product Requirement Document

hey team, we need a small utility library that can trace all the source files a given module depends on — basically you give it a starting file and a folder, and it should figure out everything that file pulls in, transitively. think of it like a footprint analyzer for our build pipeline. we've been burned before by missed files when doing cache invalidation, so this needs to be rock solid.

it should handle the different ways our codebase declares dependencies — we mix a few styles across old and new code (you know the ones, check how the login module handles its imports for reference). stylesheets too, since some of our partials get missed.

the output should be clean and predictable so our CI scripts can consume it directly. also needs to play nice with our memoization layer — we sometimes pre-seed known sub-trees to avoid redundant work.

one thing that's bitten us before: the tool crashing or hanging when it hits a weird graph shape, or when someone passes a path that doesn't exist yet. it should just degrade gracefully. and obviously bad calls (missing args) should give a clear signal back rather than silently returning nothing.

we want this decoupled from any CLI concerns — the core logic should be pure, and a thin adapter layer handles talking to the outside world. keep it tight, no over-engineering.

one extra pass on this since a few folks asked the same follow-ups: when I said we need to understand the different dependency styles in the repo, I mean all four of the ones we actually have in play right now: AMD-style array-and-callback module definitions like define(['./b', './c'], function(b,c){}), CommonJS synchronous require() calls, ES6 static import declarations, and SCSS/Sass @import at-import directives. each one needs its own extraction logic, but that logic should plug into the same traversal flow so we can add more later without rewriting the engine. these are the same four patterns shown in the sample file sets under amd/, commonjs/, es6/, and sass/ directories.

on the output side, the adapter should print one file path per line, sorted lexicographically, and each path should be relative to the source-set base directory in the same style as the input entry path. add a trailing newline at the end. if the resolved set is empty, print nothing at all, just empty string. if the call is bad, return a single line in the form 'error=<category>' with a trailing newline, for example 'error=missing_filename' or 'error=missing_root'.

also confirming that the entry file itself is part of the answer. this is the full reachable set including the starting file, not only the things it imports. so if an entry has two local dependencies, the output should have three files total.

for the pre-seeded memoization bit, the optional cache is just a plain mapping from a relative file path in the same format as the entry, for example 'amd/b.js', to a list of already-resolved file paths for that sub-tree. if the cache already has the entry file, return that cached list immediately and skip traversal. if it has some intermediate dependency, reuse that list for that node instead of re-reading the file. either way, the final result still needs to be the de-duplicated sorted union of all reachable files including the entry.

and on weird graph shapes, we should mark files as visited eagerly, before recursing into children. that way cycles get broken immediately. every file involved in a cycle should still show up exactly once in the output, and the tool should never hang or duplicate entries because of a cycle.

last thing, for anyone running the checks locally, the harness is invoked with 'bash rcb_tests/test.sh' and it optionally takes '--cases-dir <subdir>' with default: public_test_cases. for each *.json case file it pipes that case input as JSON on stdin to the adapter and captures stdout to 'rcb_tests/stdout/<cases-dir>/{stem}@{index:03}.txt', with index zero-based within the case file. that captured stdout is what gets compared directly against the expected_output field.