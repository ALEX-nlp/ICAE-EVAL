## Product Requirement Document

Hey team, we've been getting complaints from a few dev partners who are trying to use our graph query layer on top of their existing relational tables. The core ask is pretty straightforward — they want to declare a graph once (pointing at their existing tables), run pattern-matching queries against it, and get back normal relational rows they can work with in SQL. Think of it like that 'logical view over tables' approach we discussed last sprint.

The big pain points they're hitting: (1) when they write graph traversal queries today they end up with a mess of recursive joins that break every time the schema changes, (2) they can't express 'find me all paths between these two nodes within N hops' without writing custom BFS code, and (3) there's no way to introspect what the graph looks like programmatically — they have to dig through DDL to figure out what vertex/edge tables exist.

Also, some partners mentioned that error messages are completely opaque — they get a generic crash instead of something actionable. We need errors to be categorized so they can handle them in their client code.

One more thing — there was some discussion about that 'CSR structure' approach we used in the adjacency work a while back, make sure that's still exposed correctly. Check how we handled the offset array stuff previously, the partners are depending on that for their graph analytics pipeline.

Basically: define graph, match patterns, project columns, handle paths, expose schema, give good errors. Keep it clean and modular.