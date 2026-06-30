## Product Requirement Document

hey team, we need to ship the async cache library this sprint. the core idea is pretty straightforward — devs should be able to store and fetch values by key, group them into separate logical buckets so they don't step on each other, and optionally have entries disappear after a while without manual cleanup. we talked about this back when we did the storage adapter work, so please keep the same patterns we settled on there.

couple of pain points driving this: support keeps getting tickets about stale data showing up in the UI long after it should be gone, and another team had a nasty bug where two features were accidentally sharing cache keys and corrupting each other's data. we need both of those solved cleanly.

also, the data team flagged that sometimes they need to store non-string stuff — objects, raw binary blobs, booleans, nulls — and right now everything gets mangled. we need to preserve those shapes faithfully on the way out.

bonus: some power users want to plug in their own encode/decode logic around the storage layer, and a few teams want file-backed persistence instead of in-memory only. i'm not 100% sure how the file URI thing should work exactly, just that it needs to feel like a drop-in swap, same as last time with the login module backend swap.

please make sure the internal structure doesn't turn into a god-file situation — last time that bit us hard. keep things clean and separated.

one extra pass on the expiration behavior since a couple folks asked: if a save comes in with lifetime_ms of 0, that means the entry should NEVER expire, even if the cache itself was created with a default_lifetime_ms. that’s different from leaving the lifetime off entirely, which should fall back to the default if there is one. and if there’s no default set and no per-entry lifetime is provided, that entry also never expires.

also wanted to be really explicit about absence vs real values. if we read a key that was never written, or was removed, or already expired, the value we output should be the string 'undefined', like 'foo=undefined'. that sentinel is how we represent “not there.” a real stored null is different and needs to come back as 'null'. same deal for clear: it should print its label with 'undefined' as the value, like 'clear_result=undefined'. no count, no true/false, just undefined every time no matter how much got wiped.

on the namespace side, multiple cache instances can point at the same underlying store object, so isolation has to come from prefixing every stored key with the namespace string, like 'alpha:foo' vs 'beta:foo'. because of that, remove and clear in one namespace can’t touch anything belonging to another one.

for binary data, the input format is JSON objects with a '$bytes_base64' key holding the base64 payload, for example {"$bytes_base64": "YmFy"}. when we print that back out, it should be rendered as 'bytes:<base64string>', for example 'bytes:YmFy'. if that kind of bytes value shows up nested inside a plain object, the object should still be JSON-serialized, just with the nested bytes turned into those 'bytes:<base64string>' strings.

and on the pluggable backend piece, this should follow the same storage adapter abstraction pattern we used before: a backend URI, like a file path, gets passed to the cache constructor as a drop-in replacement for the default in-memory store, with the same public interface and a swappable backend.