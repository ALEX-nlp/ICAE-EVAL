## Product Requirement Document

Hey team, we need to build out this graph computation service that our data pipeline team keeps asking about. Basically it reads a JSON blob from stdin and spits out plain text results — should be pretty self-contained. The tricky part is making sure the outputs are always deterministic and reproducible regardless of how the internals work, since different engineers might implement this differently and we need consistent results across environments.

There are a bunch of operations we need to support — the usual stuff like looking up neighbors, checking if edges exist, doing traversals, finding shortest paths (both weighted and unweighted), spanning trees, that kind of thing. Also need the cycle detection and the component partitioning thing we talked about in the architecture review.

One thing that burned us last time with the login module compatibility logic — make sure errors come back as clean neutral category strings, not whatever the runtime throws. Nobody downstream wants to parse Java stack traces or Python exceptions.

Also the ordering thing is critical — wherever results could come out in random order, we need them sorted canonically so tests don't flake. I know we had issues with this on the old graph service.

Oh and there should be a test runner script under rcb_tests/ that can point at a directory of JSON cases and tell us pass/fail. The cases themselves have an input and expected_output field. Target is all 24 ops working correctly.