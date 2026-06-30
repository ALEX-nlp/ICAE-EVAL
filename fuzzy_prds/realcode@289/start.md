## Product Requirement Document

Hey team, we need to get this web-native bridge toolkit wrapped up. The core idea is that our mobile app embeds web content and right now every team that uses it ends up writing the same boilerplate glue code to talk between the web layer and the native side — parsing messages coming in, building reply messages going out, figuring out why a page failed to load, that kind of thing. It's a mess and everyone's doing it slightly differently.

We need a clean library that handles all of this consistently. Things like reading structured data out of web messages, sending replies back, dealing with those annoying JSON converter situations (you know the two cases we always hit), summarizing page load responses without dumping the whole HTML, categorizing HTTP failures and browser-level errors and SSL cert problems, and then the path config + routing logic — basically the same approach we used for the route matching in the login flow, just applied here.

One thing that keeps biting us: when HTML is really long we don't want to log the whole thing, just enough context from both ends. And the routing needs to handle those sneaky credential-stuffed URLs properly — we got burned by that before.

The whole thing needs to be structured properly, not one giant file. Tests should drive it. Can someone pick this up and make sure all the edge cases from the existing test suite are covered?