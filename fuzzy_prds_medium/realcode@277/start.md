## Product Requirement Document

hey team, picking this up from the backlog — we need to finish wiring up the scan builder for the dynogels adapter. basically right now if someone tries to do a full-table read with any kind of filtering it either blows up or silently drops conditions. the query builder already works (refer to how we handled the partition-scoped read stuff, same pattern) so this should be mostly parallel to that.

the main ask: when you chain conditions on the scan builder, they should all get AND-ed together in the output filter expression. placeholder names for attributes and placeholder values for the operands need to be collected and deduplicated — if the same attribute shows up in two conditions you can't just reuse the same placeholder key, you need to suffix it somehow (check how we did this on the query side).

also needs to support the IN operator for set-membership checks — a bunch of users have complained that filtering by a list of known values doesn't work at all on full scans.

date values used as filter operands should come out as ISO strings, not raw epoch numbers. nested attribute paths (like address.city) need to expand into the segmented name placeholder format.

projection lists and parallel scan segment config should also be reflected in the final params object. non-happy-path stuff — bad options, empty builder, etc — should fail cleanly without leaking internals.

table name always comes from the call site, not the config.

one extra pass on the scan builder details since a few folks asked how close this should track the query side. this really should mirror the query builder implementation in feature9_query_params and its corresponding core module — specifically how it accumulates ExpressionAttributeNames, ExpressionAttributeValues, and builds the expression string with parenthesized clauses joined by AND. same general idea here: every chained filter becomes its own parenthesized clause and the final filter expression joins them with AND.

for placeholder behavior, the split is important. when the same attribute shows up more than once, value placeholders are the thing that get deduped, not the name placeholders. so the first value uses the plain placeholder like `:email`, then the next ones for that same attribute become `:email_2`, `:email_3`, and so on starting at `_2`. but the attribute name placeholder is shared, so `#email` should be reused across all those conditions and only show up once in ExpressionAttributeNames.

for `in`, it takes an array of values and should render exactly in the shape `(#attrName IN (:placeholder_1,:placeholder_2,...))`. each item in that array gets its own value placeholder using the same suffixing rules as everything else, and the attribute side still has just one name placeholder entry. keep the whole `in` clause wrapped in parentheses.

for nested paths like `address.city`, expand them by segment in ExpressionAttributeNames so each part gets its own entry and the expression uses the dotted placeholder form like `#address.#city`. internally the placeholder key should use the underscore-joined version so we avoid dot collisions, and yes this is the same place the generic `#segment` pattern comes into play.

and just to restate the date bit very explicitly: if a filter operand is a Date, serialize it to an ISO-8601 instant string before it goes into ExpressionAttributeValues, like `2024-01-15T10:30:00.000Z`. we should not end up with raw epoch numbers or Date objects in the final output.