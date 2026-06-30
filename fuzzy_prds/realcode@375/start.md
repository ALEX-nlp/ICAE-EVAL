## Product Requirement Document

Hey team, we need a small clock display utility for the home screen widget. Basically users have been complaining that the time shown on different screens looks inconsistent — sometimes it's single digit hours with no padding, sometimes things jump around. It's a mess and it's all because every screen is doing its own thing.

What we need is one central place that handles the time formatting so everything looks the same. It should support the two display styles our users care about — you know, the standard full-day format and the more familiar half-day style (similar to what we did in the settings panel, refer to that folding logic). The half-day one is a bit tricky around noon and midnight so make sure those edge cases are handled correctly.

The thing needs to be callable from a test harness that feeds it JSON over stdin and prints results to stdout. Errors should come back in a clean, predictable way — not raw crash text that leaks implementation details.

Also important: keep the actual formatting brain separate from the input/output plumbing. We had issues last time where rendering logic got tangled with HTTP stuff and it was a nightmare to test. Don't repeat that.

Output should have the rendered time and also echo back which display style was used so callers can confirm what path ran. Test runner should save raw output files per case so we can diff them easily.