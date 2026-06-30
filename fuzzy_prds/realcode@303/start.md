## Product Requirement Document

Hey team, we need to build out this HTTP-to-backend transcoding layer we've been talking about. Basically the idea is: clients send normal HTTP requests with JSON bodies, and we need to route them to the right handler and convert everything into our internal message format — and do the reverse for responses. Think of it like that API gateway translation work we did on the billing service, but generalized.

The big pain points we're hearing from developers: they keep writing the same URL parsing and JSON mapping glue code over and over, it's inconsistent across services, and whenever someone adds a new endpoint they have to touch like five different files. We want one declarative place to define routes and schemas.

The system needs to handle path patterns with variables (including nested ones), action-style suffixes at the end of paths (you know, the colon thing), query parameter extraction, and both single-message and streaming flows in both directions. There's also some nuance around how percent-encoded characters in URLs get decoded — single-segment vs multi-segment captures behave differently, which has been a bug source.

For the message format side, field names come in camelCase from JSON but need to map to the snake_case internal names. Unknown fields should just be dropped. We also need to support placing a JSON body under a specific sub-field rather than at the top level.

More detailed specs are in the usual place. Please make this production-grade, not a quick hack.