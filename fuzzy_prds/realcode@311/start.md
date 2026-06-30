## Product Requirement Document

Hey team, we need to get the lambda-api serverless adapter project wrapped up. Basically the idea is that right now our backend devs are writing the same boilerplate over and over every time they spin up a new Lambda function — manually unpacking gateway events, building response objects by hand, dealing with cookies, headers, all that stuff. It's a mess and we keep seeing bugs pop up around edge cases like special characters in cookies or headers not being lowercased consistently.

We need a proper routing layer that works the way our express-style stuff does internally — you know, similar to the pattern we used on that API gateway normalization project a while back. It should handle path params, wildcards, middleware chaining, and be able to short-circuit when something goes wrong. Error handling is a big one — right now exceptions bubble up in weird ways and clients see stack traces sometimes which is obviously not great.

Also the cloud event normalization piece is important — we need it to work cleanly with both the gateway v1/v2 formats and the load balancer format since we use all three depending on the service. Cookie encoding has been a pain point specifically; there were complaints about URLs and special chars not surviving the round-trip correctly.

Can someone make sure the response envelope format is locked down and consistent? The downstream consumers are parsing that output programmatically so any variance breaks things. Let's keep it tight.