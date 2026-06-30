## Product Requirement Document

Hey team, we need to build out the form rendering helper for the Bootstrap UI project. Basically the idea is that devs shouldn't have to hand-write all that repetitive Bootstrap form markup every time — labels, inputs, wrappers, error states, the whole thing. We want something where you describe your data entity once and the library spits out the right HTML.

The big thing we keep getting burned on is consistency — missing aria stuff, wrong classes on error states, that kind of thing. We also need it to handle those input group decorators (you know, the prefix/suffix icons and buttons), and it should compose nicely with the validation error display we discussed. There's also that alignment/layout stuff — inline, horizontal, the grid column config — make sure invalid alignment values fail gracefully like we do elsewhere in the codebase, don't just silently produce garbage markup.

Also, please follow the same attribute ordering convention we settled on for the HTML output — check how the existing control renderers do it. And the feedback tooltip mode needs to work alongside the positioning context thing, similar to how we handled it in the label suppression feature.

One more thing: the spacing utility on form groups needs to be configurable at multiple levels (global default, per-form, per-control), and disabling it should remove the class entirely. Make sure closing a form resets any form-level overrides so the next form doesn't inherit them.