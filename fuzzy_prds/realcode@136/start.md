## Product Requirement Document

Hey team, we need to build out that result wrapper library we've been talking about. Basically the idea is that whenever a service method runs, instead of throwing exceptions or returning nulls all over the place, it returns one of these envelope objects that tells the caller what happened. Think of it like that pattern we used in the payments module — same vibe but more generalized.

The envelope needs to cover the usual outcomes: things went fine and here's your data, things went fine but there's no data to return, something blew up with error messages, the input was bad and we have field-level details, the thing wasn't found, or the caller doesn't have permission. We also need a paged variant for list endpoints.

One thing product keeps asking about is being able to chain these results without writing a bunch of if-statements — like if the first step succeeds you automatically flow into the next transformation, but if it already failed you just pass the failure along untouched.

Also, ops has been complaining that when a void operation fails (like a fire-and-forget write that errors out) we can't easily bubble that failure up through a method that's supposed to return actual data. Need to handle that case cleanly.

The library should expose a consistent snapshot of any result for debugging — something uniform we can log. Validation failures in particular need to carry enough detail to be useful (field name, message, and a few other bits). Let me know if you have questions, I'll try to dig up the old spec doc.