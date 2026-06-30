## Product Requirement Document

Hey team, we need to build that headless routing core we've been talking about. Basically it's a small engine that figures out which parts of the app are 'active' based on the current URL, and lets us drive navigation through plain store actions. Think of it like the matching logic we wired up in the auth flow last quarter but generalized — same idea of registering patterns and querying results, but now it's the single source of truth for the whole app.

The tricky bits are: URLs can have extra junk at the end (filters, anchors, etc.) that shouldn't break matching, some route segments are optional so they need to still show up even when nothing's there, and we definitely don't want the engine mangling any encoded characters in the URL values — that caused a bug last time.

On the action side, one of the three command types has a side effect baked in — it should talk to the browser history as part of being created, not separately. And the reducer needs to handle the case where nobody passes in a starting state gracefully.

For querying state, components need to ask things like 'is this specific route active', 'are ANY routes active right now', and 'give me the params for this route'. The whole thing should be split into sensible modules, not one big file. Can someone pick this up? We need test coverage against the JSON contract format we agreed on.