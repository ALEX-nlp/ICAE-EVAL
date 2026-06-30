## Product Requirement Document

Hey team, we need a CLI network traffic monitor tool — something that can show which process/connection is eating bandwidth in real time. The output should be plain text so it works in automated pipelines too, not just interactive terminals.

A few things I know we need: there should be a way to format bandwidth numbers nicely (we've had complaints that raw byte counts are unreadable), and the grouping should cover processes, individual connections, and remote endpoints separately. The refresh behavior should feel like snapshots — each window independent.

One thing I'm fuzzy on is exactly how the unit scaling works for the different number formats. I remember we had something similar in the login module's formatting helpers — just make it consistent with whatever we settled on there. Also not sure if we want hostname display always on or configurable — probably worth asking.

The adapter layer needs to stay decoupled from the core logic, similar to how we structured the last reporting service. The test harness should dump raw stdout into files per case so we can diff them easily. Cases live under the test directory and the runner should support pointing at different subdirectories without clobbering previous results.

Main open questions: how exactly do we pick which scale tier to display, what unit symbols do we use for each family, and does name resolution need an on/off switch at runtime?

Quick follow-up after the questions that came in: for the unit handling, there are exactly four unit families: `bin_bytes` (binary bytes, powers of 1024), `bin_bits` (binary bits, powers of 1024 after ×8), `si_bytes` (SI bytes, powers of 1000), and `si_bits` (SI bits, powers of 1000 after ×8). For binary byte display specifically, use B, KiB, MiB, GiB, TiB, PiB, with scale thresholds at powers of 1024. The piece that should own this is the bandwidth unit formatting logic in the core domain (`format_bandwidth`), specifically the scale-selection and symbol-mapping rules for the four unit families defined in Feature 1 of start.md.

Also pinning down the row shapes so nobody has to guess. A process row format is: `process: <TIMESTAMP_REMOVED> "<pid>" up/down Bps: <up>/<down> connections: <count>` where up and down are integer bytes-per-second for that window. A connection row format is: `connection: <TIMESTAMP_REMOVED> <interface_name>:<local_port> => <remote_host>:<remote_port> (<protocol>) up/down Bps: <up>/<down> process: "<pid>"`. A remote_address row format is: `remote_address: <TIMESTAMP_REMOVED> <host_or_ip> up/down Bps: <up>/<down> connections: <count>`. On the meaning of up/down, upload (up) bytes are packets sent from the local host to a remote endpoint; download (down) bytes are packets received from a remote endpoint. Bytes-per-second values are integers computed over the refresh window duration.

For the snapshot output, each refresh section ends with a blank line, so literally `\n\n` after the last row. Then the next `Refreshing:` header immediately follows with no additional separator.

And one more concrete detail for the test output path since that came up: the harness writes one file per case to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. For example, the first case (index 0) in `feature1_bandwidth_units.json` run with `--cases-dir public_test_cases` produces `rcb_tests/stdout/public_test_cases/feature1_bandwidth_units@000.txt`. Those files contain only raw stdout, no PASS/FAIL metadata.