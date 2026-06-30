## Product Requirement Document

hey team, we need to get this binary parsing adapter thing wrapped up. the idea is basically that someone hands us a JSON blob describing what kind of binary data to read, and we run the appropriate parsing logic and spit out a flat key=value output. think of it like how we handled the config reader on that older serialization module — same vibe where inputs drive behavior without the caller needing to know internals.

the tricky parts are around the edge cases: like what happens when a marker byte doesn't match what we expect, or when a read fails partway through a variant and we need to decide whether to surface each individual failure or just collapse it into a single 'nothing matched' kind of message. also there's some nuance around reads that are allowed to fail gracefully vs ones that should hard-fail the whole record.

we also need to handle things like text inside binary streams (including the wide character flavor), sequences with separators between items, and cases where an earlier value in the stream controls how many bytes come later without itself showing up in the output.

output format should be stable and consistent — downstream tooling depends on it. errors need to include position info where relevant. please make sure the core parsing logic stays totally separate from the stdin/stdout plumbing, we got burned on that last time. ideally this is structured as a proper multi-file project, not one giant file.