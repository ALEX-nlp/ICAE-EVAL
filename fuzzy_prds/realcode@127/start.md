## Product Requirement Document

Hey team, we need to get this serializer toolkit wrapped up. The core idea is that API consumers shouldn't have to get back giant payloads when they only need a couple of fields, and we also want to avoid accidentally leaking internal database IDs in URLs or responses. Think of it like what we discussed back when we built the sparse fields thing for the dashboard — same philosophy but more robust and covering nested relationships too.

Right now the pain points we're hearing from the front-end team are: (1) responses are too fat by default and they have to strip data client-side, (2) when they POST related records they're not sure if the identifier they sent was actually valid or just silently dropped, and (3) the URLs we expose contain raw numeric IDs which the security team flagged.

We also need it to handle cases where someone asks for a field that doesn't exist — right now it just silently ignores it and the front-end has no idea their query param was a typo. Same for when someone asks for both a parent object and one of its children at the same time, that should be an error too.

There's also the request context wiring — query params like `only`, `exclude`, `expand` etc. should flow through automatically, but serializer-level attribute defaults should act as fallbacks when no query params are present (check how we handled the override priority in that earlier PR). Status codes and lookup tokens need to survive through the API response wrapper as well.