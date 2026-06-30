## Product Requirement Document

Hey team, we've been getting complaints from some of our integration partners about the config/data exchange layer we built on top of that YAML library. A few things have come up that need to be addressed:

1. Partners are saying that when they send us documents with anchors and aliases, things blow up in unexpected ways instead of giving a clean error message. We need the same kind of 'polite rejection' behavior we did for that login module compatibility stuff.

2. The type discrimination feature isn't behaving consistently — apparently there are two modes for figuring out what 'kind' of object something is, and neither one is properly guarding against missing info. Clients keep getting cryptic crashes instead of a helpful message saying what went wrong.

3. On the writing side, partners want more control over how strings look in the output. Right now everything seems to get quoted the same way regardless of content, and some downstream parsers choke on that. There's also a request to suppress 'boring default' fields from the output to keep payloads lean.

4. A few folks have hit issues where they send us a null document or a null field on something that shouldn't be null, and the error they get back doesn't tell them where in the document the problem is.

5. We also need the key naming in output documents to match whatever convention the partner uses — some want snake_case, others want camel, etc.

Basically we just need this whole layer to be more predictable and informative. Can someone take a pass at this?

Quick follow-up from the questions that came in: anchors and aliases are forbidden by default, and when we hit one we should return a structured error instead of blowing up. The category needs to be `forbidden_anchor_or_alias`, the detail should say 'Parsing anchors and aliases is disabled.', and we need 1-based location info for the actual anchor or alias node. If someone really does need them, they can opt in with `anchorsAndAliases` set to `"permitted"`. There’s also an optional `maxAliasCount` integer for limiting total alias expansions, and if that limit is exceeded it should still come back as `forbidden_anchor_or_alias`, with detail 'Maximum number of aliases has been reached.' and the line/column for the alias that pushed it over.

One other related detail: `extensionDefinitionPrefix` is how we identify root-level mapping keys that are just there to hold anchor definitions. Any root key starting with that prefix should be treated as an anchor-definition block and stripped before we decode into the target shape, so it won’t cause unknown-property errors. The example here is `extensionDefinitionPrefix` set to `"."`, where a key like `.some-extension` should be treated as an anchor holder and ignored during decoding.

On the error reporting side, all error outputs need to include `line=` and `column=` using 1-based indexing for the YAML node that actually caused the failure. For missing-property and unexpected-null cases at the root, that means line 1, column 1 at the start of the root mapping. For property-value problems, point to the start of the value node for that key, not the key itself. Also, if the whole document is the null token `null`, then if the requested shape ends with `?` the result is JSON `null`; otherwise we return `error=unexpected_null` with `line=1`, `column=1`, and `path=<root>`. Same idea recursively for nullable vs non-nullable fields inside objects.

For the polymorphism piece, there are three styles under `polymorphismStyle`. `"tag"` reads the concrete type from a YAML tag like `!<sealedInt>`. `"property"` reads it from a mapping key, with the name defaulting to `"type"` unless `polymorphismPropertyName` overrides it. `"none"` turns polymorphism off entirely, and if a tag shows up in that mode we raise `incorrect_type`. Missing tag should come back as `missing_type_tag`, and when that happens inside a property it should surface as `invalid_property_value` with `cause=missing_type_tag`. Missing discriminator property is `missing_property`. Unknown tag or discriminator value is `unknown_type`, and that needs a `known=` field with the known type names comma-separated.

Also on encoding, when we write a polymorphic value with `polymorphismStyle: "tag"`, we should emit the YAML tag `!<typeName>` on the line before the mapping body. With `polymorphismStyle: "property"`, we inject a leading key, default name `type` unless `polymorphismPropertyName` says otherwise, and its value is the type name as a string, followed by the rest of that concrete subtype’s properties.

And just to close the loop on the anchor behavior, this should follow the same structured error pattern we use everywhere else: the `forbidden_anchor_or_alias` response should be a proper error with category, detail, line, and column, not a crash.