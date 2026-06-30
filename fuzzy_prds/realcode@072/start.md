## Product Requirement Document

Hey team, we need to wrap up the autocomplete search widget thing we've been building. The basic idea is that there's a read-only field on the form, and when users tap it, a search overlay pops up so they can type and pick a value. We need this to work for both single-pick and multi-pick scenarios.

A few things came up from user feedback recently: people are saying the overlay sometimes stays open when it shouldn't, or doesn't open at all when they tap the field — we need to make sure the open/close logic is solid and that we also support a mode where the parent screen controls the overlay manually (like we did with that modal pattern from the login flow).

Also, the search results sometimes feel laggy or jumpy — we need the search wiring to handle both instant local data and async remote calls cleanly, including when the remote call fails.

For display, selected values should show up correctly in the closed field — including when the data is a nested object, which has been a pain point. And when someone clears their selection, the field should go blank immediately.

Finally, teams using this in different screens want to customize labels, button text, CSS state classes, and inject their own template content into the overlay. Make sure cleanup works too — no ghost overlays hanging around after the component is torn down.