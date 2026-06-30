## Product Requirement Document

Hey team, we need to wrap up that synthetic data generator library we've been building. The core engine is mostly spec'd out but I want to make sure the adapter layer is wired up correctly before we ship. Basically the idea is that devs can feed in a JSON blob with a seed and some params, and get back a formatted string they can use in fixtures, test forms, API mocks, etc.

There are roughly 20 different generation scenarios we need to cover — things like names, credentials, network stuff, addresses, banking IDs, commerce fields, and so on. A few edge cases I'm worried about: the error handling story needs to be clean and language-neutral (remember how we handled that in the login module compatibility layer?), and there are a couple of identifier types that require embedded checksum logic — make sure those actually validate, don't just generate noise.

Also the slug/URL feature should strip punctuation properly (we had a bug with this in the old pipeline), and the placeholder text feature needs to support multiple sizing modes — exact counts, ranges, and pick-lists — not just one.

Architecturally, please don't dump everything in one file. The I/O routing, core logic, and formatting need to be separate concerns. SOLID principles apply. We want this extensible without touching the engine every time someone adds a new generator. Seed-based determinism is a hard requirement for all features.