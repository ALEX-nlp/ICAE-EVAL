## Product Requirement Document

Hey team, we need to wrap up the config + media metadata utility work we discussed in the last sprint. The goal is basically a small library that handles all the annoying boilerplate around reading app settings and dealing with media records. Think of it like that config-merging pattern we used in the old player backend — same idea but cleaner.

On the config side, we need typed setting conversion (strings, secrets, booleans, lists, ports, etc.), the ability to pull settings from multiple sources and merge them, and some way to preserve user comments when we round-trip config files. The secret type needs special handling for display vs raw output — users were complaining that credentials were showing up in logs.

For media stuff, we need immutable record types for artists, albums, tracks, playlists, and queue entries. They should serialize nicely to JSON and support non-destructive updates. There was also a reported bug where artist ordering was causing false 'changed' alerts downstream, so equality checks need to be order-insensitive for those collections.

Also need locale-aware error message decoding (hex-encoded bytes were breaking the error reporter on some EU deployments) and the XDG directory resolver that reads from env vars and falls back to the standard user-dirs config file. Port the fallback logic from how we handled it in the platform utils — you know the one.

Please wire everything up so it reads JSON commands from stdin and writes results to stdout for test harness compatibility.