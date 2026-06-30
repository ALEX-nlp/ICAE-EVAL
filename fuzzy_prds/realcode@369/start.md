## Product Requirement Document

Hey team, we need to wire up the recurring billing adapter properly. Right now devs are spending way too much time hand-rolling payment state glue code every time we add a new billing flow. The big ask is to get the adapter reading JSON from stdin and spitting clean key=value lines to stdout so our black-box test harness can validate everything end-to-end.

A few things that came up in the last sprint retro: money handling keeps breaking when people pass amounts in different formats — same problem we had with that currency rounding thing in the checkout module a while back, so make sure that's consistent. Also the coupon discount behaviour for first payments needs to reflect as a negative line item, not just a reduced total. The webhook side is particularly fragile right now — both the order-payment path and the first-payment path need to go through the proper HTTP controller/route and return the right HTTP status alongside all the state changes.

For the subscription checkout payload, trial logic needs to be baked in — someone on the gateway team mentioned the sequence type and locale fields keep getting dropped. Collection-level stuff (currency grouping, totals, error handling for mixed currencies) also needs to be solid.

Basically: clean separation between the core domain and the I/O adapter layer, no god files, and make sure edge cases like lookup failures on webhooks behave differently depending on the debug flag. Ping me if anything is unclear.