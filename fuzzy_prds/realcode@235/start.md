## Product Requirement Document

Hey team, we need a small utility library built out — think of it as the Swiss Army knife we keep wishing we had across projects. Basically every new codebase ends up with someone hand-rolling the same boring stuff: splitting up delimited text, poking at JSON blobs, doing math on strings people paste in, collecting results from a chain of operations, dealing with fixed-position records, making tests not flaky because of real-world clocks, and making sure we don't accidentally log someone's credit card number.

The idea is to expose all of this as clean, reusable contracts so we stop copy-pasting fragile one-offs everywhere. For the test harness piece, it should work similarly to how we set up the runner on the payments service last quarter — same kind of namespaced output folders so different test runs don't stomp on each other.

One thing that keeps biting us: the masking feature needs to handle that 'partial reveal' scenario (you know, show a few characters at the start and end, hide the middle), not just the all-or-nothing case. Also the clock stuff — we need both the kind you nudge manually AND the kind that just ticks itself forward on every read, since different test scenarios need different behavior.

Please make sure the adapter layer stays totally separate from the actual logic — last time someone tangled those together it was a nightmare to maintain. Output should go to stdout only, no metadata mixed in.