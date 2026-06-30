## Product Requirement Document

Hey team, we need to build out that saga testing toolkit we've been talking about. The core idea is that devs should be able to test their workflow logic without having to spin up real stores or actual network calls — basically a way to verify what a workflow *does* without caring about *how* it does it internally. There are two modes we talked about: one where you go step by step and check each instruction one at a time (kind of like that debugger flow we did in the auth module a while back), and another where you just let the whole thing run and check the results after the fact without caring about order.

The step-by-step mode needs to support rewinding, bookmarking spots, restarting with different inputs, cutting it short early, and throwing errors in to test recovery paths. If someone tries to go back further than they've gone or jump to a bookmark that doesn't exist, we should surface a clean error category — not just blow up.

The run-to-completion mode should support mocking out function calls (either returning a value or throwing), intercepting state reads, wiring up a real reducer so state updates propagate, and dispatching actions the workflow is waiting on. If a workflow is stuck waiting forever, it should still time out gracefully.

Also there's a small utility for serializing action-matching patterns to strings that needs to be included. Multi-file structure is a must — no giant single files please.