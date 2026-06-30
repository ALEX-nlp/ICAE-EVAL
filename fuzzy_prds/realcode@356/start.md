## Product Requirement Document

Hey team, we need to wrap up the QR encoding library we've been working on. The core pieces are mostly specced out but I want to make sure we're handling all the edge cases properly before we ship. Basically the library needs to handle a few different ways of turning data into QR-ready output — raw numbers packed into bits, plain byte arrays, digit-only strings, and then the full matrix rendering pipeline. The matrix stuff is the most complex part since it involves picking the right size automatically when no size is given, and also supporting manual size overrides when callers want explicit control.

One thing I keep getting questions about is the mask handling — similar to how we locked down the validation rules on that numeric input path, we need the same kind of clean error surfacing when someone passes a mask value that's out of range. The error messages need to be normalized, no raw exception dumps leaking out to callers.

Also for the matrix rendering we need two flavors — one that takes a plain text string and one that takes raw byte values directly, both should produce identical output for equivalent payloads. Auto-version selection should always pick the smallest version that fits.

The bit packing foundation underpins everything so that needs to be airtight — MSB first, fixed-width writes, zero-padded partial bytes. Refer to how the numeric grouping logic handles the trailing group sizes, same philosophy applies throughout.