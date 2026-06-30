## Product Requirement Document

hey team, picking this up from the backlog — we need to finish wiring up the scan builder for the dynogels adapter. basically right now if someone tries to do a full-table read with any kind of filtering it either blows up or silently drops conditions. the query builder already works (refer to how we handled the partition-scoped read stuff, same pattern) so this should be mostly parallel to that.

the main ask: when you chain conditions on the scan builder, they should all get AND-ed together in the output filter expression. placeholder names for attributes and placeholder values for the operands need to be collected and deduplicated — if the same attribute shows up in two conditions you can't just reuse the same placeholder key, you need to suffix it somehow (check how we did this on the query side).

also needs to support the IN operator for set-membership checks — a bunch of users have complained that filtering by a list of known values doesn't work at all on full scans.

date values used as filter operands should come out as ISO strings, not raw epoch numbers. nested attribute paths (like address.city) need to expand into the segmented name placeholder format.

projection lists and parallel scan segment config should also be reflected in the final params object. non-happy-path stuff — bad options, empty builder, etc — should fail cleanly without leaking internals.

table name always comes from the call site, not the config.