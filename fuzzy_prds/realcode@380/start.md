## Product Requirement Document

Hey team, we need to build out that physics toolkit we've been talking about — the one that lets devs work with collision shapes, bodies, and joints without writing all the low-level math themselves. Think of it like what we did with the rendering abstraction layer last quarter, but for 2D rigid-body simulation stuff.

Basically devs should be able to create circular and rectangular collision shapes and ask them geometry questions (size, boundaries, how far a point is from the edge, that kind of thing). Bodies should have some flags and gravity behavior — there was a complaint from the mobile team that fast-moving objects were clipping through walls, so we need a way to handle that. The world itself should track gravity, and bodies should be able to opt out or scale down how much they're affected.

Contacts between fixtures need a simple on/off toggle. Constraints between bodies need a full lifecycle — create, query, destroy — and when a body goes away its connections should clean up automatically. Some constraint types have motor settings that should wake up the attached bodies when changed. Each constraint type also needs to emit some kind of debug lines so devs can visualize what's connected. There's also a coupled-constraint type that combines two joints and should gracefully reject invalid combinations.

Output formatting should follow the same pattern we used in the last simulation module — two decimal places throughout. Let me know if anything is unclear.