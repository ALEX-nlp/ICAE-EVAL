## Product Requirement Document

Hey team, we need a small utility library for the new MySQL driver work. Basically it's a handful of leaf-level helpers that sit below the socket layer — things the driver needs to do correctly before it even opens a connection. We've had bugs in the past where placeholders inside quoted strings got counted as real parameters, or version strings with weird formats caused crashes, so we need solid implementations of all that stuff.

The six areas are: parsing SQL with placeholders (both positional and named), reading the server's version banner (including that MariaDB quirk we handle the same way as the old compatibility logic), decoding the column flag bits from result metadata, looking up a column by name with MySQL's matching rules, figuring out if a host string is an IP literal, and safely quoting identifiers.

The tricky parts are the edge cases — negative version components, the special binary-collation behavior for the flag decoder, backtick-forced exact matching in the name resolver, and the leading-zero / first-octet rules for IPv4. We've seen silent failures when these are wrong and they're really hard to debug at the wire level.

Entry point should read JSON from stdin, one command per run, and write plain-text key=value output to stdout. Should be small, repository-native implementation for simplicity. Let me know if anything is unclear — some of the rules I'm describing come from internal notes that might need a second look.