## Product Requirement Document

Hey team, we need to build out that lightweight inference runner we've been talking about. The idea is that our data science folks export a trained model once, and then any production service can just run it without needing the whole training framework installed. We had a similar portability story with that config-loading module from the auth service — same vibe here, just for neural nets.

The runner needs to handle a few different evaluation styles: the standard layered one, a sequence-folding one for time-series stuff, and a more flexible graph-based one for complex routing. Each style reads a self-contained model description and spits out named results as plain text.

One thing that came up in ops review: some of our input pipelines occasionally produce bad values (missing sensors, overflow, that kind of thing) and we need the runner to handle those gracefully rather than blowing up. Also, the output formatting needs to be totally consistent across environments — our diff-based monitoring will flag any whitespace or precision drift as an incident.

Architecture-wise, please don't make this a single giant file — last time that happened with the analytics batch job it was a nightmare to maintain. Keep the parsing, math, evaluation strategies, and I/O handling clearly separated.

Errors should come out in a normalized text format, not raw stack traces or framework exceptions, since downstream log parsers don't know how to handle those.