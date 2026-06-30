## Product Requirement Document

hey team, so we need to build out this terminal table rendering thing for the ride comparison CLI. basically travelers are complaining that the current output is really hard to read — prices from different providers are showing up in inconsistent formats, and when multiple cars have the same pickup time it just lists them separately which wastes screen space and looks cluttered. we want something clean and box-drawn like those fancy terminal UIs.

the renderer needs to handle two views: one for pricing comparisons and one for wait times. for pricing, it should show each option with its fare, how far the trip is, how long it takes, and whether there's any price surge happening. for wait times, it should group options that arrive at the same time together instead of repeating rows.

we talked about this in the last sprint — remember how we handled the multi-currency stuff in that billing display module? same idea here, different currencies in the same list should each show their own symbol. also the time formatting should work the same way across both views, consistent with how we did the duration display in that earlier feature.

borders should use that gray styling we agreed on. the whole thing should be a library with clean separation — not just one big file dumping everything to stdout. input comes in as a structured object and you get back a finished string. invalid inputs should fail gracefully.