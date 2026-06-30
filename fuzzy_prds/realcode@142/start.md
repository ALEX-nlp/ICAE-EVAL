## Product Requirement Document

Hey team, we need a spell-checking CLI tool for our source repos. The idea is pretty straightforward — we've been accumulating tons of typos in comments and docs across multiple codebases and it's becoming embarrassing when external contributors notice them. We want something that only flags words we *know* are wrong (no false positives from identifiers or jargon), and can optionally just fix them automatically in-place.

Basically it should scan files or whole directories, tell you where the typos are (file + line), and suggest corrections. When fixing automatically it should be smart about capitalization — like if someone typed a word in all-caps it should fix it in all-caps too, same deal with title case.

We also need ways to suppress certain words from being reported (both inline and from a file), skip certain files by pattern, and handle weird encodings gracefully. There's also that summary mode we talked about in the last sprint — same approach we used for the login module audit tool, so refer to that for how the tallying should look.

One thing I keep forgetting to mention: the quiet flag behavior — it's a bitmask thing, not just a boolean. Make sure whoever implements this checks how bit 16 specifically is supposed to work with the file-rewrite notifications. Also need proper error handling if someone points it at a dictionary file that doesn't exist. The word-boundary logic matters too — by default underscores should keep things glued together.