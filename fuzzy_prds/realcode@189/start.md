## Product Requirement Document

Hey team, we need to build that CI config generator tool we've been talking about. The idea is that each package in the repo just has a small config file describing what SDKs to target and what steps to run, and then this tool spits out the full Travis CI setup plus a shell runner script automatically. No more hand-editing that giant YAML every time someone adds a new package.

A few things I know are important: packages should be able to share work when they're doing the same thing (why run the same check twice?), and when packages disagree on step ordering we should catch that early and tell the developer clearly instead of silently generating something broken. There's also some logic around how different task names that end up doing the same underlying thing should be handled — kinda like the deduplication approach we used in that billing pipeline refactor.

The tool also needs to read an optional root-level config file for repo-wide settings, and it should complain loudly if someone references a step name that doesn't actually exist anywhere. Validation of the per-package files should happen before anything is written out.

One more thing — there's a flag for how dependencies get fetched in the generated script, default behavior vs the alternative mode. Make sure warnings about SDK version mismatches and unused SDK declarations still show up in the console output even when we do generate successfully.