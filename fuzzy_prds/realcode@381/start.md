## Product Requirement Document

Hey team, we need to get this binary serialization thing shipped. The basic idea is we have structured data (records with various field types) and we want to convert them to bytes and back again reliably. Think of it like our own compact wire format — similar to what we did with that encoding layer in the transport module, but more self-contained.

The tricky parts are: we need to handle ALL the primitive types including the weird ones like dates (stored as ticks, similar to how the calendar service does it), GUIDs in that mixed-endian layout we've used before, and those 64-bit integers that JS can't represent natively so they come in as strings. We also need nested stuff — maps, arrays, unions with discriminators, enumerations with different backing sizes.

There's also this decode-only operation where someone hands us a pre-baked hex blob and we need to parse it into a known shape (songs catalog format, I think it was spec'd somewhere in the test fixtures). Oh and constants/flags resolution needs to work too — the bit-flag enum has some combined members and even a negative one, make sure those compute correctly.

The output format for decoded records needs to be deterministic — fields in alphabetical order, maps in wire order. Floats have special string representations for infinity/NaN. Please just refer to how the existing round-trip tests expect the output to look, that's the contract.