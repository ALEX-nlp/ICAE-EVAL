## Product Requirement Document

Hey team, we've been getting complaints from integration partners that our messaging layer is basically a black box — they keep running into silent data corruption when passing structured payloads back and forth, and nobody can figure out why until it's already in prod. We need a proper codec + framing engine that handles all the low-level wire stuff so devs don't have to hand-roll byte manipulation every time.

The big pain points: nested data structures (like maps-of-maps or lists-with-mixed-types) need to survive a full encode/decode cycle without losing type info. Auth handshakes are a recurring headache — the three real mechanisms work fine but there's this 'base' one that apparently should explicitly refuse rather than silently do nothing. Also the error reporting is a mess — when something goes wrong during encoding or frame parsing, partners are getting raw stack traces instead of clean categorized errors.

There's also the chunked body reassembly thing — large messages get split across multiple transport envelopes and we need to track readiness correctly as pieces arrive.

For structure, refer to how we handled the separation of concerns in that codec module from the py-amqp work — same philosophy applies here. Multi-file layout, nothing crammed into one giant file.

Output from all operations should go to stdout in the agreed line-oriented format. cc @backend-infra for the frame writer/handler pieces specifically.