## Product Requirement Document

Hey team, we need to ship that API response toolkit we've been talking about. The idea is pretty straightforward — devs are sick of hand-rolling the same JSON envelope boilerplate every time they build an endpoint. We need something that handles wrapping successful payloads, dealing with errors, and all the pagination stuff (both the page-number kind and the cursor-based one we did for the feed feature). 

Also important: there's some validation logic around HTTP status ranges — like you can't return a 'success' wrapper with a 400-level code, that kind of thing. We burned ourselves on that before. Make sure that's locked down.

The response object itself needs to be inspectable — clients downstream (like our test harness) need to be able to peek at the status, headers, body, and the raw JSON string separately. There's also that sparse fields thing the frontend team keeps asking about — they only want specific keys back, and if the resource label is missing it should fail gracefully, not silently.

Oh and remember how we handled the side-loaded relations on the articles endpoint? Same pattern here — strip the envelope off each relation before attaching it. The decorator chain behavior should follow what we agreed on in the last architecture sync. Ping me if unclear, but basically status and success flags get prepended in order.