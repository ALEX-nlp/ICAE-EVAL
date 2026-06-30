## Product Requirement Document

hey team, we need a small utility library that can trace all the source files a given module depends on — basically you give it a starting file and a folder, and it should figure out everything that file pulls in, transitively. think of it like a footprint analyzer for our build pipeline. we've been burned before by missed files when doing cache invalidation, so this needs to be rock solid.

it should handle the different ways our codebase declares dependencies — we mix a few styles across old and new code (you know the ones, check how the login module handles its imports for reference). stylesheets too, since some of our partials get missed.

the output should be clean and predictable so our CI scripts can consume it directly. also needs to play nice with our memoization layer — we sometimes pre-seed known sub-trees to avoid redundant work.

one thing that's bitten us before: the tool crashing or hanging when it hits a weird graph shape, or when someone passes a path that doesn't exist yet. it should just degrade gracefully. and obviously bad calls (missing args) should give a clear signal back rather than silently returning nothing.

we want this decoupled from any CLI concerns — the core logic should be pure, and a thin adapter layer handles talking to the outside world. keep it tight, no over-engineering.