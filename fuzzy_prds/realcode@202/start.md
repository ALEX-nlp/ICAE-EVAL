## Product Requirement Document

We need a lightweight, framework-agnostic set of utility helpers that power our form management system. The core idea is to efficiently track what changed in a form so we only notify the listeners that actually care about the changed parts — similar to how we avoid unnecessary redraws in our rendering pipeline.

Specifically, we need the following capabilities:

1. A cheap way to check if two values are 'the same' at one level of depth — good enough for most cases without doing a full deep comparison.
2. A way to detect if a value looks like an async result that we'll need to await.
3. A caching wrapper for any calculation so it only re-runs when its inputs meaningfully changed (using our cheap comparison from above).
4. The ability to read and write values inside deeply nested data structures using a string path like we use in the config module — handle it the same way as the path resolution in our config lookup system.
5. Two kinds of change detection filters: one for tracking changes on a single field, one for tracking changes on the whole form — both should only pass along what the listener asked for.
6. A way to take raw internal field bookkeeping and produce the clean public-facing view that consumers expect, including whether the field has been touched, whether it's valid, and whether it diverged from the initial state.

All of these must be pure transformations with no side effects. Error cases should produce a predictable, machine-readable response rather than crashing. Booleans should render as their literal text, missing values as a specific absence marker, and objects as compact serialized form.