## Product Requirement Document

Hey team, we need to ship that API response toolkit we've been talking about. The idea is pretty straightforward — devs are sick of hand-rolling the same JSON envelope boilerplate every time they build an endpoint. We need something that handles wrapping successful payloads, dealing with errors, and all the pagination stuff (both the page-number kind and the cursor-based one we did for the feed feature). 

Also important: there's some validation logic around HTTP status ranges — like you can't return a 'success' wrapper with a 400-level code, that kind of thing. We burned ourselves on that before. Make sure that's locked down.

The response object itself needs to be inspectable — clients downstream (like our test harness) need to be able to peek at the status, headers, body, and the raw JSON string separately. There's also that sparse fields thing the frontend team keeps asking about — they only want specific keys back, and if the resource label is missing it should fail gracefully, not silently.

Oh and remember how we handled the side-loaded relations on the articles endpoint? Same pattern here — strip the envelope off each relation before attaching it. The decorator chain behavior should follow what we agreed on in the last architecture sync. Ping me if unclear, but basically status and success flags get prepended in order.

One quick follow-up from the questions that came in: for the status checks, let’s be really literal about it. Success responses only accept HTTP status codes in the range 100–399 inclusive, and any status code from 400 onwards will be rejected with the normalized error output: `error=invalid_status`. Error responses only accept HTTP status codes in the range 400–599 inclusive, and any status code below 400 will be rejected with the normalized error output: `error=invalid_status`. This is the same HTTP status category validation logic in Feature 6: success responses accept 100–399, error responses accept 400–599, implemented in the status validator module of the core domain.

Also, on the resource labeling edge cases: when no data source category can be matched (dataType is `"none"` or unrecognized), the resource key resolves to `null`. The output is `{"resourceKey":null}`. Null data is classified as a `"null"` resource type, so the output includes `resourceType: "null"`, the provided `resourceKey`, and `data: null`. Scalar-object data is classified as `"item"`, and arrays of non-scalar objects are classified as `"collection"`.

For errors, the payload shape should stay flat inside the top-level wrapper. The error payload is wrapped in a top-level `error` object containing `code`, `message`, and any additional fields from the `data` input merged directly (not nested) into the error object. For example, `data: {foo: 1}` results in `{"error": {"code": "...", "message": "...", "foo": 1}}`.

On the raw response helper, `laravel_json_response` produces an object with `status` (integer), `headers` (object), `body` (decoded JSON object — the raw data passed in, not re-wrapped), and `content` (raw JSON string of the body). Unlike `build_success_response`, there is no decorator chain or data envelope applied — the data is used directly as the body.

For page-number pagination, previous and next URLs are constructed by appending the existing query parameters to the path, then appending `&page=<n>`. For example, with path `http://api.test/articles`, query `{filter: recent}`, and currentPage 2 of 3, the output is: `previous: http://api.test/articles?filter=recent&page=1`, `next: http://api.test/articles?filter=recent&page=3`. totalPages is computed as `ceil(total / perPage)`.

And just to close the loop on included relations, Feature 3 included resource merging: unwrap the `data` envelope from each relation in the `included` map before attaching it to the primary data object by relation name.