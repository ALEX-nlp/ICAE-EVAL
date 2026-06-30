## Product Requirement Document

Hey team, spinning up a ticket for the manifest generation work we discussed last sprint. Basically we need to build out the config-to-manifest pipeline for our k8s deployments. The core ask is that devs can pass in a structured config blob and get back deterministic summaries of what would be deployed — stuff like the workload spec, networking, scaling, storage, identity, monitoring hooks, and any custom extensions we bolt on.

The big pain point right now is that every team hand-rolls their own YAML and we keep seeing drift — missing labels, wrong selectors, incomplete port bindings, that kind of thing. We want one canonical way to do this.

A few things that need to work: required fields should blow up loudly when they're absent (similar to how we handled the null-value edge cases in the auth service config loader — you know the one), optional stuff should just silently fall back to defaults. Also the rollout strategy should only kick in when it's explicitly turned on, not default to something that could cause surprise restarts in prod.

We also need the CSI secret volume wiring and the managed cert stuff for GCP environments. The monitoring endpoint config should follow the same pattern we used for the service monitor setup in the platform team's last release.

Output needs to be line-oriented key=value so the deployment pipeline can parse it without a full YAML parser. Happy to clarify anything but let's get this scoped out.