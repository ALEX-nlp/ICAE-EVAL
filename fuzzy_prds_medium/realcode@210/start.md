## Product Requirement Document

Hey team, we need to build out that HTTP test client utility we've been talking about. Basically developers are spending way too much time writing the same boilerplate over and over every time they need to poke at an API endpoint — setting up headers, dealing with auth stuff, cookies, all that. It's killing velocity.

The tool should let you fire off requests and then check what came back — like, did the right status come back, is the body what we expected, are the headers correct, that kind of thing. Also needs to handle pulling values out of responses (JSON and XML both, similar to what we did in the extraction module from the data pipeline project). Schema checking would be nice too.

One thing that's come up a lot: people want to be able to template URLs so they're not hardcoding IDs everywhere. And form submissions need to work properly — not just raw bodies but the real encoded format that browsers use.

When something doesn't match, the errors need to be clean and readable — no stack traces or framework-specific exception names leaking through, just plain descriptive messages.

The core logic shouldn't be tangled up with how we read input or write output — keep it decoupled like we discussed. The adapter layer handles translation.

Let's make sure repeated query param names are handled sensibly too. Someone filed a complaint about that last sprint.

A couple extra specifics from the questions that came in: for repeated query params, we should treat the last value as the winner. So if somebody adds 'name=john' and then 'name=jane', the final query string needs to use 'name=jane'. That's the canonical deduplication rule we want here.

On the URL templating piece, path placeholders use double curly braces, so {{paramName}}. For example, '/user/{{userid}}' with userid=1 resolves to '/user/1', and that substitution needs to happen before the HTTP request is dispatched.

Also, on failure messaging, for an exact body mismatch the message needs to be exactly "Actual response body did not match expected response body.\nExpected: <expected>\nActual: <actual>". Important detail there: those '\n' values are literal escape sequences inside the single-line 'message=' field, not actual line breaks in the output. Same idea for collection matcher failures like 'item_equal' — if we expected something like 'Atlantis' and actually had ['Sun City', 'Pleasure Meadow'], the format should be "Expected elements selected by '<selector>' to match 'a collection containing \"<value>\"', but was [<actual items comma-separated>]".

For headers, the User-Agent value should always be formatted as '<product>/<version>', for example 'MyUserAgent/1.0', and the output line is 'user_agent=MyUserAgent/1.0'. That applies whether it was set directly on the request object or inherited through reusable request defaults. For basic auth, the Authorization header is 'Basic ' plus the Base64 encoding of 'username:password'. So username='username' and password='password' gives 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='. The output also needs 'authorization=basic' and 'value=Basic <encoded>' on separate lines. And for the auth work more broadly, Feature 3 authorization header construction covers both that Basic auth encoding of 'username:password' and the bearer token passthrough for token-based auth, as specified in feature3_authorization_headers.json.

Last thing to underline is the separation line: the execution adapter is the only layer that should parse JSON input and write string output. The core domain classes need to be callable directly with normal method calls and have no dependency on JSON or stdout. The adapter's job is just to translate JSON command fields into method calls on the core API, then format the result as the output string. And yes, extraction is still in scope exactly as discussed: Feature 15 (json_extraction) and Feature 16 (xml_extraction) — value extraction from HTTP response bodies using JSONPath ($.Places[0].Name style) and XPath (//Place[1]/Name style) selectors, as specified in feature15_json_extraction.json and feature16_xml_extraction.json.