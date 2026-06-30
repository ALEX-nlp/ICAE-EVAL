## Product Requirement Document

Hey team, we need a small utility layer for the push service side of things. Basically we keep copy-pasting the same glue code across services and it's causing drift — metrics labels are inconsistent, service URLs get malformed when someone forgets about default ports, and we're sending way too much broadcast traffic because nobody's doing proper delta checks. Can someone build a centralized thing that handles these three pain points?

For the client metadata side, we want to normalize incoming strings into stable labels like we did for the browser detection in that old compatibility module — same idea, 'Other' fallback for anything we don't recognize, but still surface whatever we can parse. OS and browser both need a metrics-safe label AND a human-readable field.

For the service URLs, the router always uses HTTP, the endpoint can vary. The big thing is don't show redundant port numbers — users keep seeing weird URLs with :80 or :443 appended and it looks broken.

For the broadcast delta piece, clients come in with a snapshot of what they have, and we only want to push what changed. New broadcasts shouldn't spam clients who haven't opted in yet. When nothing changed, just say so cleanly.

The whole thing needs a CLI adapter that takes JSON on stdin and spits out line-oriented text so we can black-box test it. Tests should live under rcb_tests/ and a single bash entry point should run everything.