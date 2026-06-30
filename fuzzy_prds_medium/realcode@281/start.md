## Product Requirement Document

Hey team, we've been getting complaints from integration partners that our messaging layer is basically a black box — they keep running into silent data corruption when passing structured payloads back and forth, and nobody can figure out why until it's already in prod. We need a proper codec + framing engine that handles all the low-level wire stuff so devs don't have to hand-roll byte manipulation every time.

The big pain points: nested data structures (like maps-of-maps or lists-with-mixed-types) need to survive a full encode/decode cycle without losing type info. Auth handshakes are a recurring headache — the three real mechanisms work fine but there's this 'base' one that apparently should explicitly refuse rather than silently do nothing. Also the error reporting is a mess — when something goes wrong during encoding or frame parsing, partners are getting raw stack traces instead of clean categorized errors.

There's also the chunked body reassembly thing — large messages get split across multiple transport envelopes and we need to track readiness correctly as pieces arrive.

For structure, refer to how we handled the separation of concerns in that codec module from the py-amqp work — same philosophy applies here. Multi-file layout, nothing crammed into one giant file.

Output from all operations should go to stdout in the agreed line-oriented format. cc @backend-infra for the frame writer/handler pieces specifically.

A few more specifics from the questions that came back: for `b` fields, consecutive bit arguments need to share octets, and the packing order is least-significant-bit-first. That means we keep packing a run of bits together and only flush to a whole number of bytes when a non-bit field shows up or when we hit the end of the argument list. So if there’s just one true bit in the byte, it should come out as 0x01, not 0x80.

On table/array values, integer sizing needs to be explicit. Anything inside field tables and arrays that falls outside the signed 32-bit range (-2147483648 to 2147483647) needs to go out on the wire as the 64-bit signed integer code (`l`, 0x6C). If it’s within that range, use the 32-bit signed integer code (`I`, 0x49). For long-string tagged values, when decoding an `S` / 0x53 payload, try UTF-8 first. If it’s valid UTF-8, return `str:<text>`. If it’s not valid UTF-8, return `bytes:<hex>` instead of throwing or turning it into junk text.

Also, every frame needs the same hard stop at the end: the single byte 0xCE. That applies across method frames (type 1), content-header frames (type 2), body frames (type 3), and heartbeat frames (type 8). On the error side, the abstract `AMQPError` base class and the intermediate category subclasses should default to `reply_code` of 0, while the concrete ones keep their real AMQP codes, like `NotFound` with reply_code=404. And if no details are passed in, the string form should be `<TypeName: unknown error>`.

A couple encoding details too: timestamps using format code `T` in argument lists, or tag `T`/0x54 in tables/arrays, are an unsigned 64-bit integer in 8 bytes, big-endian, representing Unix epoch seconds. If the input is an ISO-8601 datetime string, convert it to UTC epoch seconds before encoding. Decimals with tag `D`/0x44 are 1 byte scale followed by a 4-byte signed integer, big-endian, for the unscaled value. So `55.5` becomes scale=1, unscaled=555, and `-3.4` becomes scale=1, unscaled=-34.

One output formatting thing we should be consistent about: whenever we render recovered table values or message properties, all keys need to be emitted in lexicographic (alphabetical) sorted order. That includes field tables in round-trip output, message property output, and nested table values too. And yes, still stick to the multi-file `src/` split from the PRD — primitive-field codec, composite table/array codec, property/header codec, body reassembly, authentication mechanisms, frame I/O, and error model should each stay as their own cohesive module instead of drifting into one giant file.

Last bit on auth since this came up directly: the SASL hierarchy is PLAIN, AMQPLAIN, and EXTERNAL as the concrete implementations, and the abstract BASE mechanism should not pretend to work. If its initial_response gets called, it needs to return `error=not_implemented`.