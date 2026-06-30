## Product Requirement Document

Hey team, we've been getting complaints from a few power users who sync their note vaults and keep running into weird situations — stuff like emoji or Chinese characters in filenames getting mangled, binary images coming back corrupted, and occasionally their workspace config files getting silently overwritten when they pull from remote. It's basically the same kind of mess we ran into with that login module compatibility stuff, so hopefully we can reuse some of that thinking here.

The core ask is a sync engine library that handles the whole lifecycle: reading local files, comparing against a remote snapshot, figuring out what changed, safely applying updates in both directions, and surfacing conflicts in a way that doesn't just dump a stack trace on the user. There's also a thing where if the sync fails halfway through (network drops, auth expires, etc.), the next retry should pick up everything from where the last *successful* sync left off — not from the failed attempt.

One thing that came up in the retro: certain workspace paths should never be silently overwritten — they need to go into some kind of staging area instead. Same deal for files that exist locally but we've never tracked before.

We need a clean adapter layer so the engine itself isn't tangled up with I/O. Error messages should read like human sentences, not exception class names. Rough priority: get the encoding/path/state stuff solid first, then the conflict/retry behavior.