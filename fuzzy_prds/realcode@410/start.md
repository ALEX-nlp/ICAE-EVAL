## Product Requirement Document

hey team, we need to wrap up the HTTP/2 engine work we've been talking about. basically the idea is devs shouldn't have to touch raw frame bytes or worry about window accounting themselves — the library handles all that under the hood. think of it like what we did with the WebSocket abstraction layer back in Q2, same philosophy but for HTTP/2.

the main pain points we've heard from users: (1) people keep writing fragile connection code because they're manually tracking stream state and pseudo-headers, and (2) apps randomly break under load because nobody's doing proper flow-control bookkeeping. we want to fix both.

scope includes: client side sending requests and reading back responses (including weird edge cases like informational responses before the real one, trailers-only responses, etc.), server side accepting requests and writing responses, ping/keepalive plumbing so we stay live without violating the protocol, some kind of raw frame inspection utility, and the window update / overflow protection stuff.

there also needs to be a test runner that someone can just kick off with a single bash command — outputs go into a specific folder structure so CI can diff them. the adapter that drives tests should be separate from the actual protocol logic, similar to how we isolated the JSON bridge in the auth service. make sure errors come back as clean category strings, not stack traces or class names.