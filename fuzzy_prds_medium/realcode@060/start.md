## Product Requirement Document

Hey team, we need to build a widget wrapper for that reCAPTCHA thing we keep manually wiring up in every project. Sick of copy-pasting the same script tag boilerplate and then babysitting whether the grecaptcha global is ready yet before calling render. The widget should handle all of that internally — script loading, waiting for the API, rendering, the whole lifecycle. Devs should just pass in their config and get back something they can drop into a page.

Also we got a complaint last sprint that one of our pages was loading the script twice and causing a flicker — same kind of dedup logic we did for that analytics snippet in the login module, so just follow that pattern here.

The widget needs to support both the normal checkbox style and the invisible flow (the one where you call execute yourself). Custom layouts should also be possible — some teams want to wrap the challenge inside their own card component.

Errors need to be machine-readable, not just thrown exceptions with random messages, because the platform team wants to handle them in their error boundary without doing string matching.

When config changes (site key, size, theme, etc.) the challenge should refresh automatically — we had a bug before where stale config was being used after a prop update and users were getting verified against the wrong key. Make sure re-renders are covered.

One extra pass on details from the team: if nobody passes a custom CSS class, the container should just use `g-recaptcha`. And if `container_id` is omitted, the id attribute should be an empty string.

For the script itself, the injected source must be `https://recaptcha.net/recaptcha/api.js?render=explicit`. When a language is configured, append `&hl=<language>` to that URL. The script must have both `async` and `defer` attributes set to true. Also, before injecting, check whether there’s already a script tag in the document whose `src` matches the challenge provider script URL pattern. If one is already there, don’t add another one. Same outcome across multiple widget instances on one page: they should all share the same injected script, so you end up with `script_count=1` regardless of instance count. This is the same script deduplication idea: before injecting the reCAPTCHA script, check document for existing script tags whose `src` matches the recaptcha.net/recaptcha/api.js URL pattern; if found, skip injection. See feature5_script_injection.json and the script injection module.

A couple config forwarding specifics too. For visible challenges, meaning any size other than `invisible`, `badge` and `isolated` should be left out of the provider render config and show up as `undefined`, and `language` is forwarded and may be an empty string. For invisible challenges, flip that around: `language` is omitted and reported as `undefined`, while `badge` and `isolated` are forwarded to the provider.

Default-wise, if nothing is specified, `visual_theme` should default to `light`, `challenge_size` should default to `normal`, and `tab_order` should default to `0`. In invisible mode, if there’s no `badge_position` specified, `badge` should default to `bottomright` and `isolated` should default to `false`. And in rerender scenarios, if `site_key` is unspecified, the default `site_key` is `some-key`.