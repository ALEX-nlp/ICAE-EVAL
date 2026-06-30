## Product Requirement Document

Hey team, we need a JS adapter thing for the rich text editor we're bundling. Basically right now devs have to hand-write all the script tags, startup calls, plugin registrations etc. and it's a mess — people keep getting the asset URLs wrong, forgetting to strip version strings in certain places but not others, and the form rendering variables are all over the place.

The idea is: you describe what you want once, and the system spits out the exact JavaScript snippets or form-view data you need. Think of it like that asset-normalization pattern we used in the login module — same idea where some URLs need the query string removed and some don't, depending on context.

It needs to handle: resolving editor asset URLs, generating the CKEDITOR startup call with proper locale handling (remember we have those locale codes with underscores that need normalizing), registering plugins/styles/templates as separate snippets, managing named config collections with merge support, and producing form view variables for templates.

One thing that kept biting us before — raw JS expressions like regex literals inside config need to come out unquoted, not as JSON strings. And when the editor is disabled the form view should be trimmed down, not the full payload.

The whole thing should be testable via stdin/stdout JSON commands. Missing named resources should give a clean neutral error, not some internal exception message. Shouldn't be a single giant file — keep concerns separated properly.