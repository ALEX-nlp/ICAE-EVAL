## Product Requirement Document

Hey team, we need to build out that vector search utility we've been talking about. Basically developers should be able to throw a bunch of high-dimensional numeric arrays at it, search for the closest ones using a few different distance flavors, and get ranked results back. Think of it like what we did with the recommendation engine similarity layer, but standalone and reusable.

A few things I know we need: people should be able to tag their vectors with their own IDs instead of relying on internal slot numbers, search should work both in a fast approximate mode and a slow-but-exact mode, and results should survive a process restart — so some kind of save/load story is required.

We also had complaints from the data team about wasted space after they remove old entries — apparently once you delete something the slot just sits there. We need to let people reuse that capacity. And the index should be resizable if someone underestimates how many vectors they'll need upfront.

On the error side, if someone tries to pull vectors out before anything has been added, or passes in a single ID instead of a list, they should get a clean, human-readable error — not some Python stack trace or internal exception name leaking through.

Output format should be consistent and parseable — similar to the key=value style we standardized on in the metrics pipeline. Distances should be shown to 6 decimal places.