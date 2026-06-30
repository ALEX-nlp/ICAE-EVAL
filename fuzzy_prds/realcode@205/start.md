## Product Requirement Document

Hey team, we need to build out that graph/routing toolkit we've been talking about for ages. Basically devs keep rewriting the same pathfinding and matrix stuff every project and it's causing a ton of bugs and wasted time. The idea is a single library that handles all the common cases — shortest paths, maze traversal, flow networks, component grouping, that kind of thing.

The tricky part is the adapter layer — similar to how we handled the dispatcher in that earlier routing module, we want a clean JSON-in / text-out contract so our test harness can validate everything automatically. The test runner should sweep a directory of case files and dump each result into its own output file, namespaced by which case directory was used so runs don't stomp on each other.

A few things I'm not 100% clear on: how exactly should blocked vs open cells work in the maze stuff, and what does the output look like when there are multiple equally good paths? Also the assignment solver — does it always print the per-row column picks, or only sometimes? And there's some edge case around empty groups in the component stuff that I vaguely remember causing issues last time.

We also need the geo-routing scenario to confirm that two different search strategies agree on the answer. Not sure what the exact cities or distances should be — dev will need to dig into the test fixtures for that. Timeline is flexible but let's get the core contracts locked first.