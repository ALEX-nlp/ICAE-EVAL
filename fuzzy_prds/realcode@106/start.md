## Product Requirement Document

Hey team, we need a string transformation utility built out — it's been on the backlog forever and devs keep reinventing this wheel. Basically two big buckets of work: (1) renaming/casing stuff, like taking a class name and turning it into a database table name, or doing the reverse for display, and (2) making words grammatically correct in multiple languages — English obviously, but also some of the European languages we discussed in the Q3 planning doc, plus Turkish which came up from the Istanbul team's request last sprint.

For the casing side, we need the usual suspects — snake case for storage, the two camel variants for code identifiers, and some kind of title-casing thing. There was a note somewhere about how the title one should behave differently depending on what characters you consider word boundaries, kind of like how we handled the locale-aware splitting in the old login module — check that logic for reference.

For the language pluralization piece, the tricky parts are the irregular words (English has a TON of those), and languages like Portuguese where the same ending can go multiple ways. Also compound words with hyphens or underscores should still work.

Output should just be a simple key=value line. The whole thing needs to read from JSON on stdin. Needs to be clean, testable, not a giant blob of spaghetti. Should be easy to drop in a new language later without touching existing stuff.