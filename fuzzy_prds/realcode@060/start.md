## Product Requirement Document

Hey team, we need to build a widget wrapper for that reCAPTCHA thing we keep manually wiring up in every project. Sick of copy-pasting the same script tag boilerplate and then babysitting whether the grecaptcha global is ready yet before calling render. The widget should handle all of that internally — script loading, waiting for the API, rendering, the whole lifecycle. Devs should just pass in their config and get back something they can drop into a page.

Also we got a complaint last sprint that one of our pages was loading the script twice and causing a flicker — same kind of dedup logic we did for that analytics snippet in the login module, so just follow that pattern here.

The widget needs to support both the normal checkbox style and the invisible flow (the one where you call execute yourself). Custom layouts should also be possible — some teams want to wrap the challenge inside their own card component.

Errors need to be machine-readable, not just thrown exceptions with random messages, because the platform team wants to handle them in their error boundary without doing string matching.

When config changes (site key, size, theme, etc.) the challenge should refresh automatically — we had a bug before where stale config was being used after a prop update and users were getting verified against the wrong key. Make sure re-renders are covered.