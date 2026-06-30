## Product Requirement Document

Hey team, we need to build out a text templating library — think along the lines of what we scoped out in the Q2 planning doc. The core idea is that devs can pass in a template string plus some structured data and get back rendered output. We want to support the usual stuff: variables, loops, conditionals, and the ability to plug in custom formatting functions. There's also been a lot of pain around reusable template chunks — people keep copy-pasting the same header/footer snippets everywhere, so we need a way to define and include those.

One thing that's come up from the content team is that authors keep accidentally leaving internal notes in the output — we need a way to strip those out cleanly. Also, the data science folks asked about doing simple math directly in the template rather than pre-computing everything upstream.

For error handling, we want something consistent — basically the same normalization approach we used in that parser module from the billing project, where errors get categorized and surfaced in a predictable way rather than blowing up randomly.

We also need a tokenization mode so tooling can inspect templates without actually rendering them. And there's been feedback about inconsistent whitespace around control tags — similar to the trim behavior we discussed for the notification templates last quarter. Make sure the I/O adapter stays cleanly separated from the core logic so we can test the engine in isolation.

Quick follow-up from the questions that came in: for the tokenization mode, the output goes to stdout and it’s one token per line. Literal text chunks and tag chunks each get their own line, and that includes whitespace around tags as its own separate lines too. So for example, ' {{funk}} {{so}} ' becomes ' \n{{funk}}\n \n{{so}}\n '.

On the comment behavior, we’re using block comments with {% comment %} ... {% endcomment %}. Everything inside those tags gets removed from rendered output, but literal text outside the delimiters stays exactly as-is. So 'foo{% comment %} note {% endcomment %}bar' renders as 'foobar'.

For assignment, the form is {% assign varname = expression %}. The expression can be a variable, a literal, or a filtered pipeline, and once assigned the variable is available for the rest of the current render scope. We also do want index access for arrays, so things like {{ foo[0] }}, {{ foo[1] }}, etc. should work.

On conditionals, the if tag needs to handle straight truthiness checks like {% if value %}, boolean operators 'and' and 'or' with short-circuit chaining, and comparisons ==, !=, <, >, <=, >=. If a string contains operator words, like 'foo and bar', that should still be treated as a literal string in comparisons. Nested if/else/endif is in scope, and unless is just the inverse of if.

For custom formatting functions, the registration path is through a filter module/class the engine exposes, for example Template.RegisterFilter. Each filter gets the current pipeline value as its first argument and can also take extra literal or variable args. Chaining uses pipes, like {{ value | filter1 | filter2:'arg' }}. The demo filters we talked about are cite_funny, which prefixes 'LOL: ', and add_smiley, which appends a smiley argument.

Built-in filters should include the text ones escape, truncate:N, truncate_words:N, split, join, replace, strip_newlines, and newline_to_br. For clarity on truncate:N, it cuts to N chars with '...' suffix, so truncate:7 on '1234567890' yields '1234...'. Numeric filters are plus, minus, times, divided_by for integer division, and modulo. Sequence filters are size, first, last, sort, and map.

Also, on error handling, the normalization behavior is exactly the one captured in feature13_error_normalization.json: errors are categorized as 'error=syntax\n' when rethrow_errors=true, or rendered inline as 'Liquid error: <message>' otherwise, and that handling lives in the execution adapter layer. And for whitespace trimming, we do want the dash marker behavior with {%- and -%} as specified in feature12_whitespace_trimming.json, stripping leading and trailing whitespace around control tags, including tabs and newlines.