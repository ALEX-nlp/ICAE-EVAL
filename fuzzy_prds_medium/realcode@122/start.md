## Product Requirement Document

Hey team, we need a lightweight notification dispatch thing built out. The idea is that our app code should be able to trigger toast-style alerts without knowing anything about how they get rendered — basically a middleman that takes a request and broadcasts it as an event. Think of it like the pub/sub pattern we used for that modal coordination work a while back, same general philosophy.

The service needs to handle a few different flavors: standard messages at different urgency levels (you know, the usual spectrum from info to critical), and also richer notifications where you're dropping in a whole custom view widget with some optional config params. For that second type, there's some nuance around when you attach a parameter bag vs. not — it's a bit like the conditional attachment logic we discussed in the last sprint review, so dig around the existing patterns if you're unsure.

Also needs dismissal support — users are complaining that stale banners stick around too long during page transitions. Should be able to wipe everything, wipe by urgency, or wipe just the widget-style ones.

The whole thing should be wired up so the adapter layer reads commands from stdin as JSON and spits results to stdout, one field per line. Invalid inputs for the widget-style notifications should surface a clean error rather than blowing up. We'll need a test runner script too that loops through the case files and captures raw output.

One extra pass on the expected behavior since a few good questions came up. On regular show requests, if no heading is provided, we still want the field in the output every time as `heading=` with an empty value, not omitted. Also for the two ways a message can come in, `message_kind`=`text` and `message_kind`=`fragment`, they should behave the same from the outside. In both cases the message counts as attached, so output should always say `message=present`. There isn’t a valid path where message shows up as absent.

For `show_component`, the parameter bag rules are a little stricter than the first pass may have implied. If neither a parameter bag nor settings are provided, we still attach an empty parameter bag and report `parameters=present`. But if it’s a settings-only request, meaning settings are supplied and there is no explicit parameter bag, then we do not attach a parameter bag and output should be `parameters=absent`. So settings-only is the one case that suppresses the default empty bag.

Also, if the component value isn’t a valid component type, the core should raise a domain-level error and then the adapter should normalize that to exactly one stdout line: `error=invalid_component_type`. In that case nothing gets raised out to listeners and there shouldn’t be any other output lines mixed in.

One other formatting detail: `timeout` and `show_progress_bar` are only printed when settings were actually attached, so only when `settings=present`. If settings are absent, those lines should not appear at all. When they do appear, keep the natural value types, so `timeout=2` style integer and `show_progress_bar=true` style lowercase boolean.

And just to anchor the overall shape again, this should follow the publish/subscribe setup from start.md: producers call the dispatch service, the core `NotificationDispatchService` raises typed events, and then the adapter subscribes and turns those into the stdout lines.