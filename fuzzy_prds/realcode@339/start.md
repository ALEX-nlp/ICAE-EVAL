## Product Requirement Document

Hey team, we need to build out that compression/archive toolkit we've been talking about. The core idea is that users should be able to take raw bytes, run them through various compression formats, and get them back out intact — all in memory, no file system touching. We also need to handle the reading/writing side of things for binary data (think header parsing, integer decoding, that kind of thing). Checksumming needs to work both as a one-shot call and as a streaming/chunked approach, similar to how we handled the incremental digest stuff in the old hash utility module.

For the archive side, we need ZIP and TAR support. ZIP should handle password-protected files (same crypto approach the old zip utility used), non-ASCII filenames, and the big-file extension. TAR needs to cover the various historical flavors and long filename extensions. Both need round-trip guarantees.

One thing that came up in review: the collection management piece needs to handle duplicate names gracefully — ask Sarah about the exact behavior we agreed on for ordering. Also the error handling story needs to be clean; external callers can't be seeing internal exceptions bubble up.

Compression-wise we need DEFLATE, zlib, gzip, bzip2, and xz. The whole thing should be organized properly — no giant single files please, we got burned on that with the old codec monolith. I/O contract goes through JSON stdin/stdout for the adapter layer.