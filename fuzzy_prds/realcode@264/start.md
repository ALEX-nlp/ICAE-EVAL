## Product Requirement Document

Hey team, we need to build a small memory allocation inspection tool — basically a CLI adapter that takes JSON over stdin and spits out normalized text so our CI pipelines can validate allocator behavior without relying on raw pointer values or platform-specific output. We've been burned too many times by flaky tests that break just because addresses changed between machines.

The tool needs to handle the usual stuff: looking up how a byte count maps to an internal bucket (including that weird edge case for zero — check how we handled the sentinel in that allocator prototype we did a while back), rounding sizes up for alignment, doing basic allocs, zeroed array-style allocs, resizes (including the null-initial case and the 'impossibly large' case), explicitly aligned allocs, and some lifecycle checks to make sure live allocations are all unique and the pool drains cleanly after freeing everything.

One thing that kept biting us before: the alignment rules for the aligned-alloc path are stricter than you'd expect — not just any power-of-two works, there's a minimum threshold. Make sure invalid alignments come back as a proper normalized error string, not a crash.

The adapter should be cleanly separated from the core logic — don't bake I/O into the domain. We want a test harness script too so the whole suite runs with a single bash command. Output files should be organized by case file and index. Ask me if anything is unclear on the bucketing ranges or the sentinel index.