## Product Requirement Document

Hey team, we need a lightweight notification dispatch thing built out. The idea is that our app code should be able to trigger toast-style alerts without knowing anything about how they get rendered — basically a middleman that takes a request and broadcasts it as an event. Think of it like the pub/sub pattern we used for that modal coordination work a while back, same general philosophy.

The service needs to handle a few different flavors: standard messages at different urgency levels (you know, the usual spectrum from info to critical), and also richer notifications where you're dropping in a whole custom view widget with some optional config params. For that second type, there's some nuance around when you attach a parameter bag vs. not — it's a bit like the conditional attachment logic we discussed in the last sprint review, so dig around the existing patterns if you're unsure.

Also needs dismissal support — users are complaining that stale banners stick around too long during page transitions. Should be able to wipe everything, wipe by urgency, or wipe just the widget-style ones.

The whole thing should be wired up so the adapter layer reads commands from stdin as JSON and spits results to stdout, one field per line. Invalid inputs for the widget-style notifications should surface a clean error rather than blowing up. We'll need a test runner script too that loops through the case files and captures raw output.