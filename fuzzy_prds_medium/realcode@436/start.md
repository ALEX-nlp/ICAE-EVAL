## Product Requirement Document

Hey team, we need a background task orchestration thing for the datenlord project. Basically the problem is that when we try to shut down the service, things go haywire — some workers are stopping before the things they depend on, which causes panics and data loss. It's been a recurring ops headache and a few customers have complained about unclean shutdowns corrupting state.

The idea is to build a library where we declare the relationships between different parts of the system once, and then when we get a kill signal or manually trigger a stop, everything winds down in the right order automatically. Kind of like how we handled the dependency ordering in that older registry module — same concept but generalized.

There are a few tricky bits: some nodes handle tons of tiny short-lived tasks and we don't want to register each one individually, so there should be some kind of batching mode for those. Also we had a bug last quarter where work was still being submitted after teardown started and silently getting dropped — that needs to be a proper error instead. And obviously OS signals (the usual termination one) should trigger the same clean shutdown path.

The whole thing should be split into sensible modules, not one giant file. The test harness should run from rcb_tests/test.sh and output files per case into a namespaced stdout folder. Let me know if anything is unclear, I can get the tech lead to clarify the node names.

Quick follow-up from the questions that came in: the node list is fixed for this and should only be Root, Metrics, BlockFlush, FuseRequest, AsyncFuse, Rpc, WriteBack, SchedulerExtender. Those are the only valid node identifiers in the dependency graph, so we’re not treating node names as open-ended here.

Also to make the intended wiring totally explicit, the graph in the graph model module is the fixed one: Root→{Metrics,BlockFlush,SchedulerExtender}, BlockFlush→{AsyncFuse,FuseRequest}, FuseRequest→{AsyncFuse,WriteBack}, AsyncFuse→{Rpc,WriteBack}. Put another way, Root depends on Metrics, BlockFlush, and SchedulerExtender. BlockFlush depends on AsyncFuse and FuseRequest. FuseRequest depends on AsyncFuse and WriteBack. AsyncFuse depends on Rpc and WriteBack. Metrics, Rpc, WriteBack, SchedulerExtender have no dependencies. That’s the graph we use for topological sort during shutdown sequencing.

For the shutdown sequencing itself, the expected order in the full example is Metrics, BlockFlush, SchedulerExtender first, all with marker 0, then FuseRequest with marker 1, then AsyncFuse with marker 2, then Rpc and WriteBack with marker 3. The main rule is a node is only torn down after every node that depends on it has already been torn down. If only some nodes are actually registered, then only those nodes should show up in output, but they should still keep that same relative order.

On the batching question, only BlockFlush and FuseRequest are GC nodes. Those are the only ones that expose the lightweight batching handle for funneling lots of short-lived tasks into one background collector. The other nodes do not support batching.

And on the late registration behavior, once shutdown has begun this needs to come back as a normalized domain error, not a panic and not a silent drop. The output in that case must be exactly two lines: first 'error=spawn_after_shutdown', then 'node=<NodeName>' with the rejected node echoed there. No exception text or runtime detail should be included.