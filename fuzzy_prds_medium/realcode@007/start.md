## Product Requirement Document

Hey team, we need a small utility that can take the raw text output from whatever disk-inspection tool a given OS uses and turn it into a clean, consistent data structure. Right now every platform does its own thing and it's a mess. The idea is basically the same approach we used for that device-normalization work a while back — same kind of key/value block parsing logic.

The tool should handle two main things: parsing raw text into structured records, and knowing which inspection routine to kick off depending on what OS we're running on. If someone asks for a platform we don't support, it should fail gracefully with something machine-readable, not a Python stack trace or whatever.

One tricky bit: some of the raw output from certain tools wraps values in quotes, and some has trailing commas, so the parser needs to clean those up. Also lines that don't have a proper value — or are just bare text with no separator — should still be captured, just with a null marker.

The whole thing needs a test runner that reads case files from a directory and dumps each result to a separate output file for comparison. Should be invokable with a simple bash command. Keep the parsing logic totally separate from any stdin/stdout wiring — we want to be able to unit-test the core without any I/O gymnastics.

Quick follow-up from the questions that came in: if the input is absent, an empty string, or whitespace-only, the parser should return the empty-object sentinel `{}` and not an empty array `[]`. That’s intentional so we can tell “nothing to report” apart from “a list with no items.” For that situation, the JSON output is exactly `{}
`.

Also, the raw text should be treated as records separated by blank lines, and then each non-blank line inside a record is a `key: value` pair. If there are trailing blank lines after the last record, just ignore them — they should not create an extra empty record. And we do need to preserve order exactly as it showed up, both for the records themselves and for the keys inside each record.

On cleanup rules, if a parsed value ends with a single trailing comma, strip that one comma and leave any internal commas alone. So `foo,bar,baz,` should become `foo,bar,baz`. Same idea with quoted values: if the raw inspection output gives us something like `device: "/dev/sda"`, strip the surrounding double-quotes so the stored value is just the literal content without the quotation marks. That should apply the same way everywhere.

One other thing to be explicit about: there are two different ways a key should map to null. If there’s a colon but nothing after it, like `hello:`, that means key `hello`, value null. And if it’s just a bare line with no colon at all, like `hello`, that also means key `hello`, value null. In that second case, the full line text is the key verbatim, including any embedded spaces.

So really this is just locking in the `key: value` block parsing logic described in Feature 1 of start.md, specifically the record-splitting, null-value, trailing-comma, and quote-stripping rules that form the parser's contract.