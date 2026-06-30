## Product Requirement Document

Hey team, we need to build out this developer stat card toolkit thing — basically a system that takes in some GitHub profile data and spits out embeddable SVG cards. There are a few different card types: a general profile summary, a languages breakdown, and a single repo card. We also need some utility stuff underneath like number formatting for big counts, text sanitization so user names don't break the markup, a way to arrange card elements in a row or column evenly, and color theming so people can customize their cards or fall back to a default look.

For the scoring piece, refer to how we handled weighted metric normalization in that ranking module we discussed — it should map activity numbers into a letter grade, similar to what the analytics team outlined last quarter.

The whole thing should be structured cleanly, not one giant file. Each concern should live in its own module. There's also an adapter layer that reads JSON from stdin and writes results to stdout — that part should stay totally separate from the actual logic.

One tricky bit: possessive names on the profile card header need to handle the grammar edge case correctly (you know, names ending in certain letters). Also the card heights need to adjust dynamically based on what's hidden, but with a floor so it never gets too small.

We have some test cases already written up so you can validate against those. Let me know if anything's unclear.