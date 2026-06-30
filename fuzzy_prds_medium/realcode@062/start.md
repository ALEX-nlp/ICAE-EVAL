## Product Requirement Document

Hey team, filing this here so we don't lose track. We need a tool that auto-generates those boilerplate constants files for our Java/Kotlin projects at build time. Right now devs are hand-writing these things and they keep going stale or getting out of sync between prod and test code. Super painful.

Basically someone describes what constants they want (name, type, value) somewhere in the build config, and the tool spits out a ready-to-compile source file in the right place. Should work for both Java and Kotlin. For Kotlin remember we talked about two different ways to emit the constants — check how we handled the shape-selection in that output formatting module from the previous sprint, same idea applies here.

Also important: test-only constants should NOT bleed into production source. Keep them separate.

One thing that came up in the infra discussion — if nothing has changed between builds, we shouldn't be regenerating these files from scratch. The build system should recognize the outputs are still valid and pull from cache. Changing any input (including the shape/style option) must bust that cache.

If a project doesn't bother specifying a namespace/package, the tool should figure out something reasonable on its own rather than blowing up. Oh and if someone adds a second constants class alongside the primary one, both should get emitted in the same run.

Let me know if anything is unclear, I'll try to dig up the old notes.

Quick follow-up after the questions that came in. On the namespace bit, if nobody sets one explicitly, we should derive it from project_name by replacing any character that is not a valid Java/Kotlin identifier character with underscores. That means stuff like hyphens, dots, and spaces get swapped out. For example, 'test-project' becomes 'test_project'. That sanitized value is what we use both for the package declaration in the generated source and for the directory path segment under the output root. This lives in the configuration resolution layer, so by the time generation happens we already have the default package/namespace string ready to use in both places.

Also wanted to be extra clear on test output behavior. When source_set is 'test', the task name needs to be 'generateTestBuildConfig', not 'generateBuildConfig'. The output path should use 'test' instead of 'main' in that source-group slot, like build/generated/sources/buildConfig/test/..., and the generated class name should be prefixed with 'Test', so for example 'TestBuildConfig'. In that mode we only emit the fields listed under test_fields for that file. The production fields are ignored for that task invocation, which keeps the test-only stuff from leaking over.

For Kotlin, there are still two supported shapes. The default is 'object_container', which means everything goes inside 'internal object BuildConfig { ... }'. If output_style is set to 'top_level_constants', then we emit file-scope constants with no enclosing object, just the package declaration, imports, and bare 'internal const val' declarations. In both cases the file name and path stay BuildConfig.kt. The output_style field in the input config is what picks between 'object_container' and 'top_level_constants', and that should be handled in the Kotlin source generator / code-writer piece that actually renders the file structure.

On caching, the expectation is pretty specific: if we run a clean build twice with the same inputs, the second one should come back FROM_CACHE rather than SUCCESS. If any input changes, including the output_style option, that cached result needs to be invalidated and the task should run again with outcome SUCCESS. The cache check mode writes lines like first_build_status, first_generate_outcome, second_build_status, second_generate_outcome, and sometimes third_* to stdout, so that’s the stuff we should be lining up with.

Last thing, for extra generated types: when extra_types is present, each entry should produce another source file alongside the main BuildConfig file in the same task run. Each one has its own type_name and its own fields list. Both files land under the same namespace/package directory, and stdout should print each file separately with its own '--- source ---' / '--- end source ---' block. Primary file first, then the extra types in declaration order.