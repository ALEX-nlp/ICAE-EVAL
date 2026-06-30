## Product Requirement Document

Hey team, we need to add a new feature to the repo service around snapshot build cleanup. Basically, after someone pushes a new snapshot build, the old build artifacts should get cleaned up automatically so we don't accumulate junk. The user-facing complaint is that storage keeps ballooning after repeated snapshot deployments and browsing those version folders gets super messy with hundreds of stale files.

The cleanup should leave behind only the metadata-related files for the snapshot version — those checksum sidecars we use everywhere need to stay (same pattern we followed for the mirror and deploy flows). Old build timestamp entries should be removed but the core metadata file and all its integrity companion files must survive.

A few things I'm not 100% sure about: how many checksum formats we actually support (I think it's the same set we standardized on for the descriptor generation work?), and whether the new timestamp needs to be tracked or just used as a trigger. Also someone mentioned something about the base version naming convention with that dash-R pattern — not sure if that affects the path structure or just the filename matching.

Path structure should follow the same conventions as the rest of the artifact storage stuff. Please check how the existing deploy and metadata modules handle version paths to stay consistent. We need this scoped to the specific version snapshot folder, not the whole artifact tree.