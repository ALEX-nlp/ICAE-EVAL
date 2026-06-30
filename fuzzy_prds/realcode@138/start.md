## Product Requirement Document

Hey team, we need to build out this cross-platform error reporting bridge thing. Basically right now our devs are complaining that they have to write a ton of boilerplate every time they want to get crash reporting working on both web and mobile at the same time — sessions are out of sync, native crash data is missing user info, that sort of thing. We want a single setup flow that just handles everything depending on what platform you're on.

The tricky parts are: (1) starting up the native side correctly without blowing up when config is missing, (2) making sure events actually get packaged up the right way before they go through the native layer (think about how that login module did the payload wrapping last time — same idea here), (3) keeping user/tag/context data in sync on the native side, and (4) there are some old severity names floating around in the wild that we need to quietly remap before they hit the bridge.

Android and iOS behave slightly differently for context data specifically — Android needs a fallback path. Also the envelope format for events has some specific shape requirements around byte length and content type that I don't fully remember, so double-check that.

Please make this a proper multi-file project, not a single blob. Tests should run with a single bash command. Needs to handle bad/missing config gracefully with real warnings, not silent failures.