## Product Requirement Document

Hey team, we need to build out the operator contract toolkit we've been discussing. The main idea is that devs shouldn't have to hand-write all the repetitive Kubernetes boilerplate every time they set up a new operator — things like resource definitions, permission rules, event records, and test wiring. Basically, you describe your resources once and the library figures out the rest.

We already have some of the scaffolding from the last CRD generation spike (you can look at how we handled versioning and group naming back then), so try to stay consistent with those patterns rather than reinventing things.

The tricky parts are: making sure schema mappings handle all the edge cases around nullable fields and special Kubernetes types, getting the permission grouping logic right so we don't end up with duplicate rule entries, and making the in-process test harness actually route lifecycle events correctly to the right handlers.

Also — and this is something that came up in last week's retrospective — there's been confusion about what happens when someone looks up a resource that doesn't exist in the cache, or tries to generate a schema for a type the system doesn't understand. We need those failure paths to produce something consistent and actionable rather than just blowing up.

The test runner adapter needs to stay completely separate from the core logic, just like we agreed. Someone will validate everything against the standard test case files once it's wired up.