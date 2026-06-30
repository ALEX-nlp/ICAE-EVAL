## Product Requirement Document

Hey team, we need to build out that session management thing for our async web framework. Basically devs are complaining they have to manually wire up cookie handling every single time they build a new endpoint — reading cookies, validating them, writing them back, all that boilerplate. It's causing bugs where sessions get saved even when nothing changed, or worse, tampered cookies aren't caught. We need something that just works automatically.

The session itself should behave like a normal Python dict so devs don't have to learn anything new. It needs to track whether it was actually touched so we don't write unnecessary cookies. We also need a few different storage options — a basic plaintext one for dev/testing and at least two secured ones for production (think along the lines of what we did for the auth tokens in the login module, same kind of key-based approach).

There's also the middleware piece — it should wrap the handler, load the session before, and only persist after if something actually changed. Edge cases like streaming responses, redirects, and invalid response types all need to be handled gracefully. If the middleware isn't installed, devs should get a clear error rather than silent weirdness.

One thing I keep hearing from security is we need protection against session replay attacks after logout. Make sure that's covered. Misconfigured keys should fail loudly at setup time, not silently at runtime.