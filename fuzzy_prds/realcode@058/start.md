## Product Requirement Document

hey team, we need to ship the async cache library this sprint. the core idea is pretty straightforward — devs should be able to store and fetch values by key, group them into separate logical buckets so they don't step on each other, and optionally have entries disappear after a while without manual cleanup. we talked about this back when we did the storage adapter work, so please keep the same patterns we settled on there.

couple of pain points driving this: support keeps getting tickets about stale data showing up in the UI long after it should be gone, and another team had a nasty bug where two features were accidentally sharing cache keys and corrupting each other's data. we need both of those solved cleanly.

also, the data team flagged that sometimes they need to store non-string stuff — objects, raw binary blobs, booleans, nulls — and right now everything gets mangled. we need to preserve those shapes faithfully on the way out.

bonus: some power users want to plug in their own encode/decode logic around the storage layer, and a few teams want file-backed persistence instead of in-memory only. i'm not 100% sure how the file URI thing should work exactly, just that it needs to feel like a drop-in swap, same as last time with the login module backend swap.

please make sure the internal structure doesn't turn into a god-file situation — last time that bit us hard. keep things clean and separated.