## Product Requirement Document

Hey team, we need a small clock display utility for the home screen widget. Basically users have been complaining that the time shown on different screens looks inconsistent — sometimes it's single digit hours with no padding, sometimes things jump around. It's a mess and it's all because every screen is doing its own thing.

What we need is one central place that handles the time formatting so everything looks the same. It should support the two display styles our users care about — you know, the standard full-day format and the more familiar half-day style (similar to what we did in the settings panel, refer to that folding logic). The half-day one is a bit tricky around noon and midnight so make sure those edge cases are handled correctly.

The thing needs to be callable from a test harness that feeds it JSON over stdin and prints results to stdout. Errors should come back in a clean, predictable way — not raw crash text that leaks implementation details.

Also important: keep the actual formatting brain separate from the input/output plumbing. We had issues last time where rendering logic got tangled with HTTP stuff and it was a nightmare to test. Don't repeat that.

Output should have the rendered time and also echo back which display style was used so callers can confirm what path ran. Test runner should save raw output files per case so we can diff them easily.

One small thing to make extra explicit since a few folks asked: the adapter needs to print exactly two lines to stdout, no more and no less. First line should be `time=HH:MM` with the rendered clock string, second line should be `mode=<mode>` echoing the resolved rendering mode, like `24h` or `12h`. There needs to be a trailing newline after each line, and we should not add any extra lines, labels, or metadata around that.

Also, on the 12-hour behavior, this is intentionally just the simple numeric fold and nothing fancier. If the hour is 12 or greater, subtract 12 from it before rendering. If the hour is less than 12, leave it as-is. So noon with hour=12 renders as `00`, hour=23 renders as `11`, and hour=9 renders as `09`. No AM/PM marker gets added. Same point as the PRD Feature 2 note: subtract 12 from the hour if it is >= 12, leave unchanged if < 12. Pure numeric fold only.

Padding should be consistent everywhere too. Both the hour and the minute always need to be zero-padded to exactly two digits in both modes. So a single-digit hour like 9 becomes `09`, and a single-digit minute like 4 becomes `04`. Separator is always one colon, so the final shape is always fixed-width `HH:MM`.

And on errors, please keep them normalized and predictable. If the command is malformed or incomplete, return a clean, language-neutral error category string, for example something indicating a missing required field or an unknown mode value. We should never let raw host-language runtime exceptions or stack traces show up on stdout. The idea is human-readable and stable without leaking implementation internals.