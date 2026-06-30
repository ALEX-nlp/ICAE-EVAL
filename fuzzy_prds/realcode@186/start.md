## Product Requirement Document

Hey team, we need a CLI network traffic monitor tool — something that can show which process/connection is eating bandwidth in real time. The output should be plain text so it works in automated pipelines too, not just interactive terminals.

A few things I know we need: there should be a way to format bandwidth numbers nicely (we've had complaints that raw byte counts are unreadable), and the grouping should cover processes, individual connections, and remote endpoints separately. The refresh behavior should feel like snapshots — each window independent.

One thing I'm fuzzy on is exactly how the unit scaling works for the different number formats. I remember we had something similar in the login module's formatting helpers — just make it consistent with whatever we settled on there. Also not sure if we want hostname display always on or configurable — probably worth asking.

The adapter layer needs to stay decoupled from the core logic, similar to how we structured the last reporting service. The test harness should dump raw stdout into files per case so we can diff them easily. Cases live under the test directory and the runner should support pointing at different subdirectories without clobbering previous results.

Main open questions: how exactly do we pick which scale tier to display, what unit symbols do we use for each family, and does name resolution need an on/off switch at runtime?