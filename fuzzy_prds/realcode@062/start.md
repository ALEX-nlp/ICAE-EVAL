## Product Requirement Document

Hey team, filing this here so we don't lose track. We need a tool that auto-generates those boilerplate constants files for our Java/Kotlin projects at build time. Right now devs are hand-writing these things and they keep going stale or getting out of sync between prod and test code. Super painful.

Basically someone describes what constants they want (name, type, value) somewhere in the build config, and the tool spits out a ready-to-compile source file in the right place. Should work for both Java and Kotlin. For Kotlin remember we talked about two different ways to emit the constants — check how we handled the shape-selection in that output formatting module from the previous sprint, same idea applies here.

Also important: test-only constants should NOT bleed into production source. Keep them separate.

One thing that came up in the infra discussion — if nothing has changed between builds, we shouldn't be regenerating these files from scratch. The build system should recognize the outputs are still valid and pull from cache. Changing any input (including the shape/style option) must bust that cache.

If a project doesn't bother specifying a namespace/package, the tool should figure out something reasonable on its own rather than blowing up. Oh and if someone adds a second constants class alongside the primary one, both should get emitted in the same run.

Let me know if anything is unclear, I'll try to dig up the old notes.