## Product Requirement Document

Hey team, we need to build out a text templating library — think along the lines of what we scoped out in the Q2 planning doc. The core idea is that devs can pass in a template string plus some structured data and get back rendered output. We want to support the usual stuff: variables, loops, conditionals, and the ability to plug in custom formatting functions. There's also been a lot of pain around reusable template chunks — people keep copy-pasting the same header/footer snippets everywhere, so we need a way to define and include those.

One thing that's come up from the content team is that authors keep accidentally leaving internal notes in the output — we need a way to strip those out cleanly. Also, the data science folks asked about doing simple math directly in the template rather than pre-computing everything upstream.

For error handling, we want something consistent — basically the same normalization approach we used in that parser module from the billing project, where errors get categorized and surfaced in a predictable way rather than blowing up randomly.

We also need a tokenization mode so tooling can inspect templates without actually rendering them. And there's been feedback about inconsistent whitespace around control tags — similar to the trim behavior we discussed for the notification templates last quarter. Make sure the I/O adapter stays cleanly separated from the core logic so we can test the engine in isolation.