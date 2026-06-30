## Product Requirement Document

hey team, we need to build out the mobile analytics tracking client SDK for android. basically devs are complaining that they have to hand-roll all the request stuff themselves and it keeps breaking in weird ways — wrong decimal formats for prices, malformed JSON for cart items, that kind of thing. we need a clean library that handles all of this for them.

the main things we need: some kind of price helper (devs keep getting the decimal formatting wrong), a checksum utility (similar to what we did for the file verification flow in that other module, you know the one), custom metadata support with both the indexed key-value style and the flat dimension fields, a cart/order serializer, a parameter builder with that 'first write wins' mode people keep asking for, URL encoding for the query strings, and a batching wrapper for sending multiple events at once.

one thing that keeps coming up in bug reports — the batching has a page size limit that devs aren't aware of, and the null/empty handling on dimensions and variables is inconsistent across implementations. also the checksum thing should degrade gracefully instead of blowing up.

we should follow the same repo structure pattern as before — nothing too over-engineered but also not one giant file. tests should be runnable with a single bash command and output files should be namespaced properly so different test runs don't stomp on each other. ping me if you need the exact wire format specs, i can dig them up.