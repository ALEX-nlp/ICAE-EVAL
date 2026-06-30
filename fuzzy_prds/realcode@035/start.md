## Product Requirement Document

Hey team, we need to wrap up the i18n routing utility for the static export project. The core idea is that we have a translation catalog (a nested dictionary keyed by language code) and we need a small runtime library that handles all the typical locale stuff — picking the right language, building navigation links, rendering translated strings, that kind of thing. We talked about this back when we did the browser-detection piece, so carry that pattern forward here.

The tricky parts I keep hearing about from the frontend folks: when someone's browser reports a regional variant like 'en-US', we should gracefully handle that (I think we strip the region part? check how we did it before). Also there are some edge cases around what happens when the URL has a language code we don't recognize — we want a sensible fallback rather than a broken page.

There's also the language switcher component — it needs to be accessible (screen readers etc.) and correctly wire up the router navigation, including preserving any other query params already in the URL. Oh and template strings in translations should support some kind of variable interpolation.

The outputs need to match exactly what the test harness expects — I know there are some subtle formatting differences between the 'resolved via browser' path vs the 'normal config' path so please double check those. Reach out if anything is unclear.