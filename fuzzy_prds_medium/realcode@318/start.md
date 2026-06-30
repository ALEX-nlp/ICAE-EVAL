## Product Requirement Document

Hey team, we need to build out the core plumbing for our isomorphic component framework. This is similar to what we did for the old routing layer on the dashboard project — same general idea, just applied here more broadly across naming, URL handling, cookies, and the server-side action API.

Basically the framework needs to know how to turn a component's name into a tag and back again, handle camelCase normalization with optional prefixes (you'll know what I mean when you look at how identifiers flow through the system), match incoming URLs to application state across named 'buckets', parse and write cookies, and generate a small inline script that the browser can run to replay whatever the server decided to do (redirects, cookie writes, etc.).

There's also a method-lookup pattern — refer to how we resolved handlers on that earlier module API — where you try the specific named method first, then fall back to a generic one, then to a no-op. The no-op behavior is subtle and has caused bugs before so please be careful there.

We also need an event bus wired into the API provider with the usual on/once/off/emit, but validation needs to be strict — wrong types should surface as named error categories, not raw exceptions.

Please keep everything well-separated by concern, nothing monolithic. Ping me if anything in the routing parameter syntax is unclear, it's a bit custom.

One small follow-up after the team questions came in. For the error-name bit, the error variant is just the base component name plus the reserved suffix `--error`. If the base name is not a string, return an empty string. So `'some'` → `'some--error'`, and `null` → `''`.

On the camelCase token side, when a prefix is present, join the prefix with the name before doing camelCase normalization. Runs of non-alphanumeric separator characters get removed and the immediately following letter gets uppercased, and leading/trailing separators get trimmed. If the name is falsy or empty, the token should just be empty. The examples to stick to are prefix=`'some'`, name=`'awesome-module_name'` → `'someAwesomeModuleName'`, and with no prefix, name=`'awesome-module-name-'` → `'awesomeModuleName'`.

For cookies, the combined header should be built from the initial string first, then each added cookie appended as `key=value`, with everything joined by `; `. So initial `'some=value; some2=value2'` plus `some3=value3` and `some4=value4` becomes `'some=value; some2=value2; some3=value3; some4=value4'`. Also on the server-side provider, the environment flags are static and fixed there: `isBrowser` is `false` and `isServer` is `true`.

For the event bus validation, if someone subscribes or removes using a non-function handler argument, surface `invalid_event_handler`. If they subscribe using a non-string event name, surface `invalid_event_name`. These should stay as neutral domain-level error categories, not raw exceptions. Behavior-wise, `on` fires every time the event is emitted, `once` fires exactly once on the first emission and then removes itself, and anything removed should not fire.

On the inline replay script, the output is wrapped in a `<script>…</script>` tag. Redirects should emit `window.location.assign('<uri>');`. Cookie writes should emit `window.document.cookie = '<key>=<value>';` for each cookie. Fragment clear is supported too. If any values contain `</script>`, neutralize that so we don’t allow tag injection. If there are multiple actions, concatenate them all inside a single script tag.

For the callback adapter, this is the Node-style shape where the last argument is `(error, result)`, and we wrap that into a promise. If the callback comes back with a result, resolve with that result. If it comes back with an error, reject with the error message. The examples are `{ result: 'hello' }` → `resolved=hello` and `{ error: 'hello' }` → `rejected=hello`.

And just to be explicit on the two places people asked about most: in Feature 1.5 the method resolution should prefer camelCase prefixed method, then fallback to generic prefix method passing the entity name, then deferred no-op — same lookup behavior we called out before, matching the handler lookup pattern described in feature1_5_method_resolution.json. And for routing, use the colon-parameter route pattern syntax with bracket-delimited store lists defined in Feature 2.2 (feature2_2_route_state.json), including path/query parameter capture, percent-decoding, and query-override-path rules.