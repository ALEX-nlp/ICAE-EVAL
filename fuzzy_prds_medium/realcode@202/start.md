## Product Requirement Document

We need a lightweight, framework-agnostic set of utility helpers that power our form management system. The core idea is to efficiently track what changed in a form so we only notify the listeners that actually care about the changed parts — similar to how we avoid unnecessary redraws in our rendering pipeline.

Specifically, we need the following capabilities:

1. A cheap way to check if two values are 'the same' at one level of depth — good enough for most cases without doing a full deep comparison.
2. A way to detect if a value looks like an async result that we'll need to await.
3. A caching wrapper for any calculation so it only re-runs when its inputs meaningfully changed (using our cheap comparison from above).
4. The ability to read and write values inside deeply nested data structures using a string path like we use in the config module — handle it the same way as the path resolution in our config lookup system.
5. Two kinds of change detection filters: one for tracking changes on a single field, one for tracking changes on the whole form — both should only pass along what the listener asked for.
6. A way to take raw internal field bookkeeping and produce the clean public-facing view that consumers expect, including whether the field has been touched, whether it's valid, and whether it diverged from the initial state.

All of these must be pure transformations with no side effects. Error cases should produce a predictable, machine-readable response rather than crashing. Booleans should render as their literal text, missing values as a specific absence marker, and objects as compact serialized form.

A couple extra details from the team’s questions. On the cheap equality check, shallowEqual never recurses, so it’s really only doing the one-level pass with strict equality (===) at depth-1. That means two different nested object references do not count as equal even if they look the same. For example, shallowEqual({c: {}}, {c: {}}) returns false because the nested {} objects are different references and strict equality (===) is used at depth-1.

For async detection, because JSON cannot carry a real function, a member whose value is the string '@@fn' denotes a callable member in the wire protocol. So an object with {"then": "@@fn"} is thenable (returns true). An object with {"then": true} or any non-callable then value is not thenable (returns false).

On the memoized wrapper, the memoizer has exactly ONE cache slot. It recomputes when: (1) there is no previous call, (2) the number of arguments differs from the previous call, or (3) any positional argument is not shallowEqual to the corresponding previous argument. Argument count change always triggers recompute even if all common arguments are equal.

For paths, this is meant to line up with the toPath() / getIn() / setIn() functions in src/structure/. Path strings are split on dots and square brackets (regex /[.[\]]+/) with empty segments filtered out. This is the same tokenization used throughout the form-state engine for addressing nested values.

A small but important behavior in setIn: calling without a value argument (value=undefined) deletes the target leaf. After deletion, empty objects are pruned upward — an object that becomes empty is replaced with undefined, which cascades up. However, arrays keep their length: a removed element becomes an empty slot rendered as null in JSON output.

On the field publishing side, publishFieldState sets length: Array.isArray(value) ? value.length : undefined. If the field's current value is an array, 'length' is included in the output. If not an array, 'length' is undefined and omitted from compact JSON output (JSON.stringify omits undefined values). Including this exact phrase since it came up in review: s current value is an array. Also, after reading the error via getIn, if error exists and has a property keyed by the ARRAY_ERROR symbol (Symbol('array-error')), the error is replaced with error[ARRAY_ERROR]. This unwraps array-level errors stored under that symbol into the plain error field.

For submission state, dirtySinceLastSubmit = !!(lastSubmittedValues && !field.isEqual(getIn(lastSubmittedValues, name), value)). It is false when formState has no lastSubmittedValues (undefined/null). It is only true when lastSubmittedValues exists AND the last-submitted value differs from the current value under the configured equality function.

Last piece: the dispatch adapter routes on the 'op' field in the JSON request. Supported ops are: compare, is_thenable, cached_call, parse_path, get, set, filter_field, filter_form, publish_field. An unknown op returns 'error=unknown_op'. Missing op field also returns 'error=unknown_op'.