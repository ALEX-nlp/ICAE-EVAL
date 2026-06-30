## Product Requirement Document

hey team, we need to wrap up the SQL builder library we've been talking about. the core idea is that devs shouldn't have to hand-concatenate SQL strings anymore — they give us structured input describing what they want and we spit out the SQL + bound args. we need to handle the usual CRUD stuff plus some of the trickier bits like conditional expressions and the runner/cache integration we did for that db abstraction layer a while back.

couple things i want to make sure we nail: the placeholder handling needs to support both the question mark style AND the numbered dollar-sign style (like postgres uses), and switching between them should be seamless. also the argument ordering has to be deterministic — we've had bugs before where args get shuffled and it breaks prod queries silently.

for the runner piece, it should work similarly to how we wired up the recording adapter in the auth service — basically you inject whatever executor you want and the statement just calls through to it. same idea for the cache layer, don't re-prepare the same SQL twice.

one thing i'm fuzzy on is exactly how zero values for limit/offset should behave — make sure we handle that explicitly. error messages need to be normalized machine-readable codes, not free-form strings. reach out if you need the exact formats, i have some notes from the earlier spike somewhere.