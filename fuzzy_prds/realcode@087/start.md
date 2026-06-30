## Product Requirement Document

Hey team, we need to wrap up the storage client library work. Basically the whole thing — auth, URLs, parsing, the works. A few things I want to flag that came up in the last stakeholder review:

The signing logic needs to handle all the weird edge cases we saw in production last quarter — like when people use virtual-host bucket names vs path-style, or when there are custom metadata headers stacked up. We got burned by that before.

For the temporary link stuff, remember how we handled the escaping in that download-manager feature a while back? Same idea here — the tokens need to be URL-safe when embedded in a query string. There are two flavors: just the token itself, and the full assembled link. Make sure the bucket can optionally appear in the hostname.

There's also all the input hygiene stuff — bucket names, credentials — we need to fail fast with clear, stable error codes (not Python exceptions or whatever the runtime spits out). Same philosophy as the validation layer we built for the upload flow.

On the response side, we need to parse the XML blobs the service returns for listings, copy results, location info, and object metadata. Also handle HTTP-level errors gracefully — distinguish between 'server gave us an error document' vs 'server just died'.

One thing I keep forgetting to write down: there are rules around which query params and request headers are actually allowed on the wire — everything else should be silently dropped. Ask me if unclear.