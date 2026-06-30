## Product Requirement Document

Hey team, we need a small toolkit for the multiplayer session handshake flow. Basically when a client tries to join a host, we keep running into issues where the host can't properly verify who's connecting or whether their game setup matches. It's been causing complaints from players who get dropped or stuck in weird states at connection time.

The two main things we need: first, some kind of compact identity thing you can send over the wire that bundles the player's unique ID together with their mod version — similar to how we handled it in that login module compatibility flow we did before, just apply the same kind of strict validation logic there. It needs to go both ways, encode and decode, and it should loudly reject garbage input rather than silently accepting it.

Second, we need a way to compare the list of installed game modules between the client and host to decide if they're compatible enough to play together. There should also be a way to snapshot/export that module list so it can be transmitted and reconstructed on the other side faithfully.

The whole thing should be cleanly separated — don't just throw it all in one file. The part that handles input/output shouldn't be mixed in with the core logic. We'll be running automated tests against it so the output format needs to be exact. Timeline is pretty tight so keep it simple but correct.