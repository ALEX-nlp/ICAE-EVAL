## Product Requirement Document

Hey team, we need to build out a client transport core library for our RPC services. Basically our backend teams are spending way too much time re-writing the same boilerplate every time they wire up a new service — things like figuring out where to point requests, layering in auth/logging middleware, and dealing with weird error payloads that come back from services. It's becoming a real maintenance headache.

The core thing we need is: you give it a service address string and it should figure out all the routing info automatically. We also need some kind of middleware/interceptor system where you can stack multiple handlers and they run in the right order — people keep getting confused about which direction things fire when you have multiple layers. There's also a streaming use case where messages need to be wrapped in some kind of envelope format before sending.

Lastly, when calls fail, the error objects coming back sometimes carry extra structured context payloads (like retry hints, violation details, etc.) and right now devs are just doing string parsing which is brittle.

For the scheme validation piece, just do it the same way we handled protocol checking in that older transport module — you know the one. The test harness should follow the same pattern we used on the billing service CLI adapter.

This needs to be clean, modular code — not one giant file. Use whatever language makes sense. Ping me if you have questions!