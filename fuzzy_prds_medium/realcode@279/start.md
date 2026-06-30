## Product Requirement Document

Hey team, we need a JS adapter thing for the rich text editor we're bundling. Basically right now devs have to hand-write all the script tags, startup calls, plugin registrations etc. and it's a mess — people keep getting the asset URLs wrong, forgetting to strip version strings in certain places but not others, and the form rendering variables are all over the place.

The idea is: you describe what you want once, and the system spits out the exact JavaScript snippets or form-view data you need. Think of it like that asset-normalization pattern we used in the login module — same idea where some URLs need the query string removed and some don't, depending on context.

It needs to handle: resolving editor asset URLs, generating the CKEDITOR startup call with proper locale handling (remember we have those locale codes with underscores that need normalizing), registering plugins/styles/templates as separate snippets, managing named config collections with merge support, and producing form view variables for templates.

One thing that kept biting us before — raw JS expressions like regex literals inside config need to come out unquoted, not as JSON strings. And when the editor is disabled the form view should be trimmed down, not the full payload.

The whole thing should be testable via stdin/stdout JSON commands. Missing named resources should give a clean neutral error, not some internal exception message. Shouldn't be a single giant file — keep concerns separated properly.

Quick follow-up from the questions that came in: the URL cleanup rule is intentionally split depending on whether we’re talking about a directory-style path or an actual script file. Only the base_path has its query string stripped. The js_path keeps the full query string, including version/cache bits. So '/static/editor/?v=2' should become '/static/editor/' for base_path, but '/static/editor/editor.js?v=2' stays exactly as-is for js_path. Same rule should be reused in the asset URL normalization work and also when resolving plugin paths and contentsCss.

Also on locale handling, when we get locale strings with underscores like 'pt_BR', including when they come from locale_source='request_stack', they need to be converted to the format CKEditor expects by replacing underscores with hyphens and lowercasing the entire thing. So 'pt_BR' becomes 'pt-br', and that is the value that should land in the 'language' config key.

For named config output, the empty case should be exactly three lines: 'has_entries=no\ndefault=null\nentries=[]\n'. If there are entries, then has_entries=yes, default should show the configured default name or null, and entries should be a JSON object, not an array.

On the stdin/stdout JSON side, please keep that adapter physically and logically separate from the core logic. The adapter should just translate JSON commands into method calls on the core system. The core system should never import or depend on JSON parsing or stdin/stdout I/O directly. So this should land as a multi-file setup with distinct modules for core logic, I/O adaptation, and formatting, not one big mixed file.

One more important serialization detail: configuration values that are actually JavaScript expressions need to come out verbatim, not JSON-quoted. The specific cases here are regex literals in protectedSource arrays and selector/parser expressions. For example, '/<\?[\s\S]*?\?>/g' should be emitted as /<\?[\s\S]*?\?>/g with no surrounding quotes, while normal string values should still be JSON encoded.

And for contentsCss, those values need to go through the asset layer first with query strings stripped, then be emitted as a JSON array. The slash escaping matters here too: forward slashes in the resolved URL should appear as '\/' in the JSON output. So '/assets/theme.css' becomes '\/assets\/theme.css' inside the JSON string.