## Product Requirement Document

Hey team, we need a static analysis tool for our CI/CD config files — think GitHub Actions workflows, reusable action metadata, and GitLab pipeline configs. The idea is to parse these files into some normalized structure, figure out what third-party stuff they depend on (actions, images, includes), and flag security problems automatically instead of doing manual reviews.

Basically we keep running into the same issues: people referencing actions without pinning versions properly, workflows with overly broad permissions on triggers that could be hit by fork PRs, jobs running on self-hosted runners that shouldn't be exposed that way, secrets leaking into environment variables, that kind of thing. It's getting hard to catch these consistently as the team grows.

The whole thing should be organized cleanly — not just one giant file — separate concerns properly, keep the business logic away from stdin/stdout stuff. Should handle bad/malformed configs gracefully without crashing.

We also need it to handle that package URL normalization stuff like we talked about in the supply-chain meeting (similar to what the security team uses for the container inventory work). And the runner detection logic should match what we agreed on in the last infra review — basically the same approach as the hosted-vs-self-hosted classification we use elsewhere.

Output should be deterministic and structured so it's easy to consume downstream. Can someone pick this up?