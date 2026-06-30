## Product Requirement Document

Hey team, we need to build out this security header middleware engine we've been talking about. The basic idea is that you give it a config describing what protections you want on your HTTP responses, and it spits out the right headers automatically. No more hand-rolling these things and getting the formatting wrong.

A few things I know we need: there should be a 'batteries included' mode that just turns on everything sensible at once for teams that don't want to think about it. Individual headers should also be toggleable separately. Some of the headers have dependencies on each other — refer back to how we handled the cross-origin isolation stuff in the embedder policy discussion, the same gating logic applies here. We also need path-based rules so the data-clearing header only fires on specific routes like logout pages.

The engine reads a JSON blob on stdin and writes headers to stdout, one per line, sorted alphabetically. If something is misconfigured it should spit out a neutral error token — no stack traces, no runtime garbage, just clean error codes the frontend team can parse.

Edge cases to handle: what if someone passes in no config at all? What if they want certain paths completely ignored? The CSP stuff has some tricky quoting and deduplication rules too that we need to get right. Output should be totally deterministic.

Can someone scope this out? I think the public test cases folder has examples of expected outputs we can validate against.