## Product Requirement Document

Hey team, we need to get the Dart scaffold generator wrapped up. Users keep complaining that setting up new Dart projects is super tedious — they're manually copying boilerplate, forgetting pubspec fields, mixing up package names when their folder has hyphens or dots in it, that kind of thing. The goal is a tool that takes a template choice + some basic project info and spits out a ready-to-go folder structure.

We already have the template catalog defined somewhere in the codebase (similar to what we did for the package registry listing last quarter — check how we sorted and formatted that). The CLI needs to handle the usual flags, including a machine-readable mode for tooling integrations. When someone passes a bad template name, we should fail gracefully with a neutral error — no raw stack traces leaking out.

One thing I keep forgetting to write down: the description fields in the generated pubspec need some kind of line-wrapping treatment so they don't blow past the readable width. There's also a placeholder system for file content templating — make sure invalid variable names are caught cleanly without exposing internals.

The test harness should live under rcb_tests/ and run with a single bash command. Output files go into a stdout subdirectory. Please make sure the architecture doesn't end up as one giant file — last time we did something like this it became unmaintainable fast.