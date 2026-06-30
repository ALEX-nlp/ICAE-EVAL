## Product Requirement Document

Hey team, we need a small CLI utility for managing hosted script projects — think of it as a lightweight wrapper around the usual developer workflows. Basically devs are constantly complaining that they have to manually piece together editor links, remember which file type labels map to what, and clean up auth files from multiple spots when things go sideways. It's causing a lot of support noise.

The tool should handle a handful of things: showing helpful usage text for subcommands (similar to how we did it for the login flow in the auth module), converting project IDs into the right browser URLs, dealing with file type label translation in both directions (local ↔ remote), saving project config to disk, listing available APIs in a readable format, and gracefully handling mutation commands that aren't ready yet. Oh and logout needs to actually clean up creds from both places — we've had incidents where stale tokens caused weird behavior in CI.

For the API management piece, some subcommands are real, some are placeholders, and unknown ones should fail loudly rather than silently succeed. The output format should be consistent across all commands so our test harness can parse it easily — just flat key=value lines, nothing fancy.

Architecture-wise, keep concerns separated — don't just dump everything in one file. We want this maintainable long-term. Should be runnable as a single entry point that takes JSON on stdin.