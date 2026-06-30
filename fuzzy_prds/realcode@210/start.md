## Product Requirement Document

Hey team, we need to build out that HTTP test client utility we've been talking about. Basically developers are spending way too much time writing the same boilerplate over and over every time they need to poke at an API endpoint — setting up headers, dealing with auth stuff, cookies, all that. It's killing velocity.

The tool should let you fire off requests and then check what came back — like, did the right status come back, is the body what we expected, are the headers correct, that kind of thing. Also needs to handle pulling values out of responses (JSON and XML both, similar to what we did in the extraction module from the data pipeline project). Schema checking would be nice too.

One thing that's come up a lot: people want to be able to template URLs so they're not hardcoding IDs everywhere. And form submissions need to work properly — not just raw bodies but the real encoded format that browsers use.

When something doesn't match, the errors need to be clean and readable — no stack traces or framework-specific exception names leaking through, just plain descriptive messages.

The core logic shouldn't be tangled up with how we read input or write output — keep it decoupled like we discussed. The adapter layer handles translation.

Let's make sure repeated query param names are handled sensibly too. Someone filed a complaint about that last sprint.