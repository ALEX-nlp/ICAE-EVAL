## Product Requirement Document

Hey team, we need a background task orchestration thing for the datenlord project. Basically the problem is that when we try to shut down the service, things go haywire — some workers are stopping before the things they depend on, which causes panics and data loss. It's been a recurring ops headache and a few customers have complained about unclean shutdowns corrupting state.

The idea is to build a library where we declare the relationships between different parts of the system once, and then when we get a kill signal or manually trigger a stop, everything winds down in the right order automatically. Kind of like how we handled the dependency ordering in that older registry module — same concept but generalized.

There are a few tricky bits: some nodes handle tons of tiny short-lived tasks and we don't want to register each one individually, so there should be some kind of batching mode for those. Also we had a bug last quarter where work was still being submitted after teardown started and silently getting dropped — that needs to be a proper error instead. And obviously OS signals (the usual termination one) should trigger the same clean shutdown path.

The whole thing should be split into sensible modules, not one giant file. The test harness should run from rcb_tests/test.sh and output files per case into a namespaced stdout folder. Let me know if anything is unclear, I can get the tech lead to clarify the node names.