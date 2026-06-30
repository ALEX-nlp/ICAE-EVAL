## Product Requirement Document

Hey team, we need to get the lambda bridge adapter wrapped up. Basically the idea is that our Rails app should be able to run behind AWS gateways without us having to rewrite a bunch of stuff every time we deploy to a new gateway type. Right now every project has its own messy glue code and things keep breaking — cookies get lost, binary files come back garbled, error pages don't show up right, that kind of thing. We want one clean adapter layer that just handles all the translation under the hood.

The tricky part is we support a few different gateway shapes — you know, the newer HTTP one, the older HTTP one, the REST proxy style, and the load balancer. They all have slightly different response conventions, especially around how cookies get returned (remember how we handled the multi-value thing in that older API version? same idea here). Binary responses need special encoding treatment.

We also need it to handle the non-HTTP stuff — job queues, event bus messages, that maintenance runner thing we scoped out, and the parameter config export. And there's an installer flow for generating deployment scaffolding for both gateway modes.

There's a debug toggle that should only activate under certain env conditions — it's gated similarly to how we did it in the dev-only config check last quarter. Make sure the environment mapping strips stage prefixes properly too. Overall the output contract for each gateway type needs to stay stable and predictable.