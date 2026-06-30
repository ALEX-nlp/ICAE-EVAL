## Product Requirement Document

Hey team, we've been getting complaints from devs using our HTTP client generator that they keep running into silent misconfigurations and cryptic runtime failures when setting up API clients. Like someone spent half a day debugging why their requests were hitting the wrong endpoint just because of a trailing slash issue on the base address — that kind of thing should blow up immediately with a clear message, not silently misbehave.

We also need to make sure the tool rejects nonsensical declarations at build time rather than producing broken clients. For example, using the wrong annotation combo on a single method, or putting a body on a verb that doesn't support it — those should be caught early.

Also, there's been feedback that the interface validation isn't strict enough. Remember how we handled the compatibility checks in the interface-shape validation logic last time? We need something similar here — foreign language interfaces, unpackaged interfaces, generic interfaces should all be rejected cleanly.

The adapter output format needs to be consistent too — headers sorted, fields sorted, errors sorted when multiple apply. And the whole thing should be modular, not one giant file — separate the generator bits from the runtime bits from the adapter.

Can someone scope this out? I think the test cases in the rcb_tests folder cover most of the scenarios we care about. Let's make sure all the error categories are neutral and language-agnostic.