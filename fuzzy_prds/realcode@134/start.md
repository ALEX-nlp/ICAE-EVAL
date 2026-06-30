## Product Requirement Document

Hey team, we need to ship the modeltyper client-contract generator. The basic idea is: given a server-side data model, spit out TypeScript definitions that frontend devs can actually use without hand-writing interfaces. We've been burned too many times by stale types on the client side.

The tool needs to handle the usual stuff — columns, computed attributes (both the old-style and new accessor style), relationships, and those backed string constant sets we use for roles and similar things. There should be a way to wrap everything in a global namespace for projects that need it, and also a raw JSON metadata mode for tooling integrations.

For the constant sets specifically, remember we had that escaping issue in the auth module last time — make sure backslash-heavy values don't get mangled. Also the enum output style should be switchable between two modes (the new one uses a different type alias pattern).

We also need the discovery and inspection endpoints so downstream tooling knows which models are even valid targets — abstract or missing models should fail gracefully with a normalized error token, not a stack trace.

One thing I'm not 100% sure about: the fillable subset feature — I think it generates a Pick<> type but I forget the exact suffix convention. Check how we handled optional/hidden fields in the previous field-rendering spike. Four concrete sample models should be enough to exercise all the paths.