## Product Requirement Document

Hey team, we need to build out this page-processing library thing that the data pipeline folks have been asking about for a while. Basically the problem is that right now every team that wants to work with column pages has to write their own decoding logic before they can do any kind of row filtering or value extraction, and they keep getting it wrong especially when those weird compressed page formats come into play. We want one consistent interface they can all use.

The library needs to handle at least three kinds of page layouts — you know, the normal one, the one where every row is the same value, and the dictionary-compressed one. For the dictionary case specifically there's some tricky fallback behavior we discussed in the arch review last month that needs to be baked in.

It should support two main operations: picking which rows pass a condition (either a numeric window check or a remainder-based check, same ones we used in the billing filter module), and then pulling out the actual values for a given set of rows. Row sets can be described either as a straight range or as an explicit list.

The whole thing needs a CLI adapter that reads JSON from stdin and writes results to stdout so the test harness can drive it. There's also some metadata reporting that pipeline tooling depends on — make sure that part is stable. Please follow the same separation pattern we used on the auth refactor.