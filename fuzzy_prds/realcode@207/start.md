## Product Requirement Document

hey team, we need to finish up the metrics library work we've been discussing. basically we need something that lets services track numbers over time — things like totals that only go up, values that can go up or down, and distribution-style tracking. there's also some stuff around making sure the names people give to these metrics are actually valid before we store them — remember we had that bug last quarter where someone passed in a weird string and everything broke downstream? same kind of logic as what we did for the label sanitization in the old collector module.

also we need a way to group related metrics together and spit them out in a format that our scraping infrastructure can actually read. there's a serialization piece here that needs to handle some edge cases with special float values and escaping. and we need an HTTP layer so services can expose their metrics at a path that gets polled.

oh and there's a base64 thing too — some encoded credentials flow through the auth part of the endpoint, so we need to be able to decode those and handle bad input gracefully.

the summary metric type needs to support percentile-like estimates, which i know is the tricky one. just make sure the output matches what the scraper expects. lmk if you have questions, but a lot of this should be obvious from context.