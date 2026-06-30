## Product Requirement Document

Hey team, we've been getting complaints from some of our embedded/freestanding customers that they can't use standard printf on their targets, and they're having to hand-roll number formatting every time which is causing all sorts of inconsistencies — wrong padding, signs showing up wrong, hex values not matching what they expected, that kind of thing. We need a self-contained string formatter that handles the usual stuff: numbers (signed, unsigned, hex, octal), strings, characters, floats, pointers, all with the normal alignment and padding options people expect from C-style formatting.

One thing that came up specifically: customers are hitting weird edge cases around zero values, negative widths passed at runtime, and infinity/NaN floats. Also need to make sure the output encoding is clean — non-printable bytes need to be escaped in a specific way (refer to the same escaping convention we settled on for the debug-output module).

The engine should read a JSON request on stdin and write results to stdout. Make sure write-back destinations (the ones with no value, just a type) are handled and reported separately in the output. The JSON arg types map to specific integer widths and the narrowing behavior for short/char variants needs to match what the old formatter did.

Deliverable is a working implementation with the adapter wired up. Let me know if anything's unclear but please check the existing test fixtures first before pinging me.