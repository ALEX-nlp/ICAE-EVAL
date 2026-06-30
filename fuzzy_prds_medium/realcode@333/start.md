## Product Requirement Document

Hey team, we need to build out a client transport core library for our RPC services. Basically our backend teams are spending way too much time re-writing the same boilerplate every time they wire up a new service — things like figuring out where to point requests, layering in auth/logging middleware, and dealing with weird error payloads that come back from services. It's becoming a real maintenance headache.

The core thing we need is: you give it a service address string and it should figure out all the routing info automatically. We also need some kind of middleware/interceptor system where you can stack multiple handlers and they run in the right order — people keep getting confused about which direction things fire when you have multiple layers. There's also a streaming use case where messages need to be wrapped in some kind of envelope format before sending.

Lastly, when calls fail, the error objects coming back sometimes carry extra structured context payloads (like retry hints, violation details, etc.) and right now devs are just doing string parsing which is brittle.

For the scheme validation piece, just do it the same way we handled protocol checking in that older transport module — you know the one. The test harness should follow the same pattern we used on the billing service CLI adapter.

This needs to be clean, modular code — not one giant file. Use whatever language makes sense. Ping me if you have questions!

Quick follow-up from the questions that came in: for the address parsing piece, we only accept HTTP-family schemes. Concretely, the valid schemes are 'http' and 'https'. Anything else, including 'xhtp', 'ftp', 'grpc', needs to be rejected and normalized the same way every time. The output there should be exactly 'error=invalid_argument\n', and we should not leak any host-language exception class names or runtime message text.

Also wanted to make the filter ordering super explicit since that’s where people tend to get turned around. Outbound request filters, for both unary and streaming, run in the exact order they were registered, so first registered runs first. You should be able to see that directly in the result, where input '1,2,3,4' produces 'headers.id=1,2,3,4'. Inbound response filters, again for both unary and streaming, go the other direction: reverse registration order, so the last registered filter sees the response first. The visible result there is input '1,2,3,4' produces 'headers.id=4,3,2,1'.

On the streaming/body wrapping side, the framing happens after all outbound body filters have already run in registration order. At that point we wrap the body in a single uncompressed message envelope, and the envelope header byte must be 0. The format we want out is exactly 'envelope.header=0' on the first line and 'body=<accumulated_body_bytes>' on the second line.

One last thing on inbound streaming: before inbound streaming result filters run in reverse registration order, we need to validate that the streaming response has a valid protocol content type. Only if that validation passes do we apply the result filters. For the adapter path, make sure it provides a successful streaming response header result with a valid protocol content type when exercising that flow.