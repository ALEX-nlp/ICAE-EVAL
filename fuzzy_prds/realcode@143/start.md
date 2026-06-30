## Product Requirement Document

Hey team, we need to build out that async coordination library we've been talking about. Basically, we're getting a lot of complaints from devs that they keep writing the same boilerplate state-tracking code every time they need to wait on something async — it's messy, buggy, and nobody wants to maintain it. Think of it like what we did with the deferred pattern on the payments flow, but more general-purpose.

Core stuff we need: some kind of result object that can be pending, done, or failed. Once it's settled it shouldn't be changeable (but repeating the same settlement should probably just be fine). Devs should be able to chain work off these results, recover from failures, and cancel things that are still in-flight. Cancellation should ripple upstream through any dependency chain.

We also want batch helpers — wait for all of them, wait for just enough of them, or just get a full report of what happened without blowing up. Plus some iterator-style helpers for processing lists with optional concurrency limits.

There's also a queue thing — tasks should run in the order they were added, and we should be able to schedule a thunk and get a result object back. Oh and generator-style async sequencing would be great, similar to how we wired up the step-runner in the old pipeline module.

Finally some simple state-check helpers so you don't have to poke at internals. Timeline is flexible but let's not gold-plate it.