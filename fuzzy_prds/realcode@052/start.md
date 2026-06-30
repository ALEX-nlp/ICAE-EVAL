## Product Requirement Document

Hey team, we need to wrap up the native addon rebuild planner tool we've been discussing. The core idea is pretty straightforward — when someone switches the embedded runtime version in their Electron app, all those compiled native modules break and they have to manually figure out what to rebuild. It's a huge pain point we keep hearing about from devs on the forum.

The tool should be smart about which modules actually need rebuilding — like, don't rebuild dev-only stuff, and don't redo work that's already done for the right runtime. There should also be a way to force everything to rebuild if someone thinks their build cache is messed up, and a way to narrow it down to just one or two specific modules when you're iterating fast.

We also need it to handle that workspace/monorepo layout thing we dealt with on the metrics-service project — you know, where the lock file is up a couple levels from where you're actually working. And there's the scoped package naming situation that tripped us up before (the @org/package-name format).

The output format needs to be line-based and machine-parseable so CI scripts can consume it. Keep the internals clean — separate files for different concerns, similar to how we structured that login compatibility module. Don't dump everything in one file.

Can someone spec out the ABI number mapping and make sure the incremental skip logic is solid? Those are the two things I'm least confident about.