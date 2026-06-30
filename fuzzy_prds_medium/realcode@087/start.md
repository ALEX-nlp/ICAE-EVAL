## Product Requirement Document

Hey team, we need to wrap up the storage client library work. Basically the whole thing — auth, URLs, parsing, the works. A few things I want to flag that came up in the last stakeholder review:

The signing logic needs to handle all the weird edge cases we saw in production last quarter — like when people use virtual-host bucket names vs path-style, or when there are custom metadata headers stacked up. We got burned by that before.

For the temporary link stuff, remember how we handled the escaping in that download-manager feature a while back? Same idea here — the tokens need to be URL-safe when embedded in a query string. There are two flavors: just the token itself, and the full assembled link. Make sure the bucket can optionally appear in the hostname.

There's also all the input hygiene stuff — bucket names, credentials — we need to fail fast with clear, stable error codes (not Python exceptions or whatever the runtime spits out). Same philosophy as the validation layer we built for the upload flow.

On the response side, we need to parse the XML blobs the service returns for listings, copy results, location info, and object metadata. Also handle HTTP-level errors gracefully — distinguish between 'server gave us an error document' vs 'server just died'.

One thing I keep forgetting to write down: there are rules around which query params and request headers are actually allowed on the wire — everything else should be silently dropped. Ask me if unclear.

A couple follow-ups from the questions that came in. For the query string filtering, the only keys we keep are max_keys, prefix, marker, delimiter, max-keys, and anything else just gets dropped quietly. If an allowed key has an underscore, it goes out on the wire with a hyphen instead, so max_keys becomes max-keys. If the value is null, emit just the bare key with no equals sign, and keep the output order matching the input order.

Same deal on request headers: only content_type, content_md5, content_disposition, content_encoding, cache_control, range, if_modified_since, if_unmodified_since, if_match, if_none_match, x_amz_acl, x_amz_storage_class, x_amz_copy_source, x_amz_metadata_directive make it through, and everything else gets dropped. Underscores become hyphens here too. For range specifically, if it comes in as a dict with a 'range' key containing [start, end], render it as 'bytes=start-end'. Null values stay null. Final header output should be sorted by name.

Also, the object key validation needs to be strict: an empty key is rejected with error=invalid_object_key and key=. On URL building, object keys should be percent-encoded, so spaces go to %20, non-ASCII goes UTF-8 percent-encoded, and reserved chars like [ ] become %5B %5D. The CNAME form is only available if the bucket is virtual-host eligible, meaning valid DNS label and no underscores; otherwise cname_url= should be empty.

On the bucket rules, keep the errors stable and boring. Bucket validation should return error=invalid_bucket_name and always include name= with the offending value if the bucket is empty, matches a raw IPv4 address pattern like 10.0.0.1, is shorter than 3 characters, longer than 255 characters, or begins with a dot, hyphen, or underscore. Other than that, accept it as-is.

For credentials, both access_key_id and secret_access_key are required, and this should fail fast. If access_key_id is null/missing, return error=missing_credential and field=access_key_id. If secret_access_key is null/missing, return error=missing_credential and field=secret_access_key. If both are there, return valid=true and echo the access_key_id. Same general rule for all error reporting: categories need to stay language-independent and stable, specifically 'invalid_bucket_name', 'missing_credential', 'invalid_object_key', 'remote_error', always under error=, with extra context fields like name=, field=, category=, status= depending on the case. No Python exception class names, stack traces, or runtime suffixes.

Last bit on the temporary links: when we URL-encode the HMAC-SHA1 base64 signature token, make sure '+' becomes '%2B' and '=' becomes '%3D'. That applies to the token encoding behavior we talked about for both the token-only case and the full assembled link case.