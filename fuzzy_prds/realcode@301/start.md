## Product Requirement Document

Hey team, we need to wrap up the AI client adapter work we've been scoping out. The core idea is that devs shouldn't have to hand-roll HTTP payloads every time they talk to the model service — we want them to just pass in their prompt or history or whatever resource operation they need, and get back something clean and predictable. 

There are a bunch of input shapes we need to handle — plain strings, part arrays, full content objects, the works. Same for outputs: text rendering, tool calls, blocked response signals, all of it. We also need the cache and file resource flows to work properly end-to-end, including all the expiry/TTL stuff (just do it the same way we handled the media upload pipeline last quarter — you know the pattern). 

One thing that keeps biting us in production: when devs pass reserved headers or hit backend errors, they get raw exception dumps instead of clean error categories. That needs to be fixed — errors should be normalized, no stack traces leaking out. 

Also the conversation history validator needs to be strict — we've seen weird model behavior when histories start with the wrong role or have empty turns. And the streaming URL construction has some quirks depending on which model prefix is used. Make sure the whole thing is properly structured, not one giant file. Reach out if the expiration conflict handling isn't clear.