## Product Requirement Document

Hey team, we need to wrap up the native addon rebuild planner tool we've been discussing. The core idea is pretty straightforward — when someone switches the embedded runtime version in their Electron app, all those compiled native modules break and they have to manually figure out what to rebuild. It's a huge pain point we keep hearing about from devs on the forum.

The tool should be smart about which modules actually need rebuilding — like, don't rebuild dev-only stuff, and don't redo work that's already done for the right runtime. There should also be a way to force everything to rebuild if someone thinks their build cache is messed up, and a way to narrow it down to just one or two specific modules when you're iterating fast.

We also need it to handle that workspace/monorepo layout thing we dealt with on the metrics-service project — you know, where the lock file is up a couple levels from where you're actually working. And there's the scoped package naming situation that tripped us up before (the @org/package-name format).

The output format needs to be line-based and machine-parseable so CI scripts can consume it. Keep the internals clean — separate files for different concerns, similar to how we structured that login compatibility module. Don't dump everything in one file.

Can someone spec out the ABI number mapping and make sure the incremental skip logic is solid? Those are the two things I'm least confident about.

Quick follow-up after the team questions came in. On the ABI piece, this should be a straight lookup against the NODE_MODULE_VERSION mapping table used by Node.js, not something we calculate from the version string. So if the runtime version is 10.4.7, that maps to ABI 82. Same general idea as how Node 3.x maps to a different ABI than Node 10.x — we need to resolve the correct integer ABI from a semver runtime version string and use that for the rebuild decision.

Also, for scoped packages, we should keep using the short-name portion after the scope segment anywhere we surface or match selected modules. So for @newrelic/native-metrics, the short-name is 'native-metrics', and that’s what should show up in the selected list, not the full scoped name. Same rule for allow-list matching. The selected output should be alphabetically sorted by those short-names in lexicographic ascending order and joined by commas with no spaces, like 'selected=bcrypt,farmhash,leveldown,native-metrics,ref-napi'.

On dependency selection, the closure should only start from stuff declared under 'dependencies' and 'optionalDependencies'. Anything reachable only through 'devDependencies' stays out, even if that dev dependency happens to be native. Once a module is selected, we do still walk into its own declared dependencies to find transitive native children. That means a native child nested under a non-native parent is still in scope for rebuild if it shows up that way — like 'leveldown' under 'level' via the children array. The children array is the representation for those privately installed sub-modules.

One other thing to make explicit for the monorepo case: the plan_rebuild command has a 'buildSubdir' input field that scopes dependency selection to a sub-package. When that’s present, selection should use only that sub-package’s own dependencies/optionalDependencies closure, not the root workspace manifest.

And on structure, we should absolutely keep this split into multiple files with clear separation of concerns, same spirit as the original note. At minimum, keep graph traversal / dependency classification, ABI resolution, build-stamp comparison, project-root discovery, manifest reading, and the I/O adapter (stdin/stdout handling) as distinct units. The adapter is what translates JSON commands to core engine calls, and the core engine itself should never read stdin or write stdout directly.