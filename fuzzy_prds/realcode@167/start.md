## Product Requirement Document

Hey team, we need a small toolkit for our container auto-update agent. Basically the agent needs to figure out which containers to act on, how to talk to the registry, and how to load its own config. Right now every integration is doing this differently and we keep getting bugs where some containers get updated when they shouldn't, or credentials get handled wrong.

For the container picking logic, we need something like what we did with the opt-in/opt-out stuff in the billing service — same idea where some containers say 'yes update me' and others say 'no skip me', and we need to handle both modes plus a name-based allowlist and grouping by scope. There's also a weird edge case with leading characters on container names that keeps biting us, similar to the path handling issue we fixed in the storage module.

For registry auth, we need to encode credentials from environment variables into whatever token format the registry expects, and also figure out which server to talk to just from an image name.

For config, secrets should be loadable either inline or from a file on disk (ops team keeps asking for this), and we need to translate our connection settings into the right env vars for the Docker client. Default socket path should just work out of the box with no config.

The whole thing should be clean and composable — we want to wire these pieces together in different combinations depending on deployment mode.