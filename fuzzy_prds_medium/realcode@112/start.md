## Product Requirement Document

Hey team, we've been getting complaints from some of our embedded/freestanding customers that they can't use standard printf on their targets, and they're having to hand-roll number formatting every time which is causing all sorts of inconsistencies — wrong padding, signs showing up wrong, hex values not matching what they expected, that kind of thing. We need a self-contained string formatter that handles the usual stuff: numbers (signed, unsigned, hex, octal), strings, characters, floats, pointers, all with the normal alignment and padding options people expect from C-style formatting.

One thing that came up specifically: customers are hitting weird edge cases around zero values, negative widths passed at runtime, and infinity/NaN floats. Also need to make sure the output encoding is clean — non-printable bytes need to be escaped in a specific way (refer to the same escaping convention we settled on for the debug-output module).

The engine should read a JSON request on stdin and write results to stdout. Make sure write-back destinations (the ones with no value, just a type) are handled and reported separately in the output. The JSON arg types map to specific integer widths and the narrowing behavior for short/char variants needs to match what the old formatter did.

Deliverable is a working implementation with the adapter wired up. Let me know if anything's unclear but please check the existing test fixtures first before pinging me.

Quick follow-up after the questions that came in. On the stdout shape, the result= line is the only place where escaping rules kick in. Every printable ASCII byte is emitted verbatim there, and any non-printable byte plus the backslash character itself has to come out as \xHH, with backslash, lowercase x, and two uppercase hex digits. That applies only to result=, not the other lines. Same deal as the Execution Contract section of start.md.

Also on write-backs: if the format string includes one or more write-back conversions, meaning %n with any length modifier, the adapter should print one extra line per destination, in order, as writeback=<integer>. That integer is the number of characters produced up to the point that %n was encountered. Those lines come after the length= line. In the JSON input, those write-back args only have a 't' field and no 'v' field. The valid tags are wb_int, wb_short, wb_long, wb_char, wb_llong, wb_intmax, wb_size, wb_ptrdiff, and they map to length modifiers as (none), h, l, hh, ll, j, z, t.

For floats, f80 is the extended-precision case, basically long double when the format uses the 'L' length modifier, and f64 is the normal double case. Both of those can take either a numeric value or the strings "inf", "-inf", or "nan" in the JSON.

A couple runtime formatting edge cases to lock down too: if a dynamic width passed via * is negative, treat it as a positive width and apply left-justify (-). If a dynamic precision passed that way is negative, ignore it completely, same as if no precision had been specified.

And one tiny percent-sign gotcha since it came up: %% always emits exactly one literal percent sign and consumes no argument. If somebody puts a flag between the percents, like %-%, we still tolerate it and it behaves the same way: output is a single % and the length is 1.

Last bit, for integer narrowing, hh and h need to cast/truncate first and then do digit generation, matching the old behavior for signed/unsigned char and signed/unsigned short, same as described in features 4 and 5 of start.md.