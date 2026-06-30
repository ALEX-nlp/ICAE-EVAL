## Product Requirement Document

Hey team, we need a small parsing/routing library for the image-copy service — basically a collection of pure helper functions that run before we touch any network or cloud API. The idea is to stop having all that fragile string munging scattered everywhere and make the core logic actually testable in isolation.

We need a few things: something to pull the cloud region out of a registry hostname (you know, the managed container registry URLs we use), a credential classifier so we know whether to go fetch a secret or just use the value directly, and a parser for those object-storage archive location strings we use for image archives in the bucket system. The archive transport thing also needs to expose its scheme identifier and should flat-out reject any policy scope you throw at it — that transport just doesn't support scopes, period.

Also need a utility that reads a stream but hard-caps how much it buffers — we had that incident last quarter where an oversized payload caused memory issues, so this is important.

For the docker reference normalization, just follow the same convention we use in the login module — you'll know it when you see it in the codebase. The output format should be the same key=value style we already use in the other adapters. Make sure the test harness can be pointed at different case directories without overwriting previous runs.