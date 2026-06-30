## Product Requirement Document

We need the full assertion library behavior covered by the detailed contract. The adapter exposes checks for equality and non-equality, existence and non-existence, type membership and non-membership, numeric comparisons including less/greater and inclusive variants, pattern match and not-match, containment and exclusion for strings/arrays/object subsets, invalid operand handling, negated assertions, and deterministic human-readable diagnostics. Preserve exact pass/fail stdout from the public cases and hidden constraints.

One small follow-up from the questions that came in: for the human-readable messages, please keep the rendering format exact. Objects render as '{ k: v, k2: v2 }' with braces and colon-space, arrays render as '[ a, b, c ]' with brackets and comma-space, strings render in single quotes like 'value', regular expressions render in slash delimiters like /pattern/, and numbers render as plain digits.

Also, on the numeric comparison checks, if either operand is not a number, stop there and return exactly 'outcome=error\nerror=operand_not_a_number\n'. No comparison is attempted in that case.

And one more narrow thing on exclude: the 'exclude' relation only accepts arrays and strings as 'actual'. If 'actual' is an object, the result should be exactly 'outcome=error\nerror=unsupported_actual_type\n'.