## Product Requirement Document

Hey team, we need to build out the patch management toolkit we've been talking about. The basic idea is that devs can declare patches for their third-party dependencies and the system handles everything automatically — fetching, verifying, applying, all of it. We want this to feel like a first-class part of the dependency workflow, not a bolt-on.

A few things I know we need: patches should be describable as little records with a source location and some metadata, and those records need to survive being saved and reloaded (think lock file round-trips). We also need to group patches by which package they target and make sure the same patch doesn't get applied twice — remember how we handled the deduplication logic in the login module? Something similar here, but patches can collide in more than one way.

Patches also need to be applied at the right 'level' in the directory tree — some well-known packages have special requirements here, and there's a fallback chain similar to what we discussed in the config resolution spike. The system should support declaring patches either inline in the project config or in a separate file, and that file path situation needs to handle missing or misconfigured files gracefully without blowing up.

We also need the lock file naming to follow the active manifest name. And the download step should verify file integrity and report clearly when something doesn't match. Finally the patching tool itself should check whether it's even usable in the current environment before trying anything.