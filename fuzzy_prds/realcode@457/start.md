## Product Requirement Document

Hey team, we need to build out a media URL toolkit for our CDN integration. Basically devs are constantly complaining that building image/video delivery URLs by hand is super error-prone — wrong codes, broken overlays, messed up signatures, all that fun stuff. The goal is a library that takes declarative intent and spits out correct wire-format strings. Think transformation chains, overlay/layer descriptors, full delivery URLs, auth tokens, signature checking, some string/array/path utilities, and a config URL parser. 

For the execution layer it should read a JSON command from stdin and write line-oriented key=value output to stdout — errors should be normalized, no raw exceptions leaking out. The multi-file layout matters here; don't dump everything in one file, this is supposed to be maintainable. 

For the conditional expression stuff, just follow the same operator-mapping approach we used in that filter/expression module from the previous SDK iteration — you know the one. Similarly the text escaping rules for overlays are a bit special (double-escaping for certain chars), refer to the existing layer-encoding logic we settled on before. 

Signing tokens need HMAC-SHA256, config parsing handles the cloudinary:// scheme. Missing lifetime or empty secret should be proper error states, not just nulls. Oh and the sort-by-array fallback behavior when the order list is empty or irrelevant needs to be sensible. Make sure all edge cases are handled cleanly.