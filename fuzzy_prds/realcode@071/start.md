## Product Requirement Document

Hey team, we need to ship the build manifest emitter feature we've been talking about. Basically the idea is that after every webpack build, we want a JSON file written out that tells our deployment pipeline what files were emitted, where they live, and what URLs they'll be served from. Right now our ops guys are hand-editing these lists every release and it keeps breaking things in staging when chunk names change.

We also need it to handle the unhappy paths — like when a dependency is missing during compilation, we want a structured signal in that JSON rather than just a raw exception dump, similar to how we handled error normalization in the auth pipeline work last quarter.

There's also a request from the CDN team that we support serving assets from a different base URL than what webpack knows about, and the security folks want hash algorithm metadata attached to each asset for SRI purposes.

One thing I keep forgetting to mention: the file ordering in the output JSON matters to the frontend team — they complained last time that keys came out in random order and it broke their diffing tools. Also we need the path fields to be configurable so people can opt into relative paths instead of absolutes.

Finally, if someone reruns the build, the manifest should reflect the new state, not keep stale chunk info from the previous run. Can we make sure that's covered too?