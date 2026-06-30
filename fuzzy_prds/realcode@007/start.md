## Product Requirement Document

Hey team, we need a small utility that can take the raw text output from whatever disk-inspection tool a given OS uses and turn it into a clean, consistent data structure. Right now every platform does its own thing and it's a mess. The idea is basically the same approach we used for that device-normalization work a while back — same kind of key/value block parsing logic.

The tool should handle two main things: parsing raw text into structured records, and knowing which inspection routine to kick off depending on what OS we're running on. If someone asks for a platform we don't support, it should fail gracefully with something machine-readable, not a Python stack trace or whatever.

One tricky bit: some of the raw output from certain tools wraps values in quotes, and some has trailing commas, so the parser needs to clean those up. Also lines that don't have a proper value — or are just bare text with no separator — should still be captured, just with a null marker.

The whole thing needs a test runner that reads case files from a directory and dumps each result to a separate output file for comparison. Should be invokable with a simple bash command. Keep the parsing logic totally separate from any stdin/stdout wiring — we want to be able to unit-test the core without any I/O gymnastics.