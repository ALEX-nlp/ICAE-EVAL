## Product Requirement Document

Hey team, we need to build out that graph/routing toolkit we've been talking about for ages. Basically devs keep rewriting the same pathfinding and matrix stuff every project and it's causing a ton of bugs and wasted time. The idea is a single library that handles all the common cases — shortest paths, maze traversal, flow networks, component grouping, that kind of thing.

The tricky part is the adapter layer — similar to how we handled the dispatcher in that earlier routing module, we want a clean JSON-in / text-out contract so our test harness can validate everything automatically. The test runner should sweep a directory of case files and dump each result into its own output file, namespaced by which case directory was used so runs don't stomp on each other.

A few things I'm not 100% clear on: how exactly should blocked vs open cells work in the maze stuff, and what does the output look like when there are multiple equally good paths? Also the assignment solver — does it always print the per-row column picks, or only sometimes? And there's some edge case around empty groups in the component stuff that I vaguely remember causing issues last time.

We also need the geo-routing scenario to confirm that two different search strategies agree on the answer. Not sure what the exact cities or distances should be — dev will need to dig into the test fixtures for that. Timeline is flexible but let's get the core contracts locked first.

Quick follow-up after the team questions came in. On the harness side, the pathing for outputs should be exactly rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt, so for example the first case in feature1_1_weighted_shortest_paths.json run with --cases-dir public_test_cases goes to rcb_tests/stdout/public_test_cases/feature1_1_weighted_shortest_paths@000.txt. The case index is zero-padded to 3 digits. Also, rcb_tests/test.sh takes an optional --cases-dir <subdir> flag, and if nobody passes it we should default to test_cases, not public_test_cases. Either way, outputs always live under rcb_tests/stdout/<cases-dir>/ so different case directory runs never overwrite each other.

On the adapter bit, yes, the intended pattern is still that dedicated adapter module reads JSON from stdin, routes to the appropriate core domain method, and writes formatted text to stdout, with that kept physically separate from core business logic. We also do want the adapter's JSON command routing table, meaning the feature + scenario keys mapping to core algorithm calls, matching the same general pattern we used for the I/O translation layer before.

For the multiple-best-path question, when there are equally optimal answers we should print found=true, then the shared cost=<N>, then path_count=<N>, each on its own line before the paths line. The paths line itself should be pipe-separated inside double brackets, like paths=[[1,2,4]|[1,2,5,6,7]|[1,3,4]|[1,3,5,6,7]].

For the rotate scenario, the output is always three lines: cw_1=[...] for 90° clockwise, cw_2=[...] for 180°, and ccw_1=[...] for 90° counter-clockwise, each using the flattened row-major array of the transformed 3×3 matrix. For the standard 0–8 input, the exact outputs are cw_1=[6,3,0,7,4,1,8,5,2], cw_2=[8,7,6,5,4,3,2,1,0], and ccw_1=[2,5,8,1,4,7,0,3,6].

For assignment output, assignments=[...] is not always present. We only print that line when the scenario explicitly wants the per-row column picks. So for minimize_cranes it is just total=275 with no assignments line, and for maximize_small it prints both total=10 and assignments=[2,0,1].

And on the components edge case, in the undirected components separate_with_empty scenario, empty groups are represented with the sentinel value 18446744073709551615. The output there includes element_count, group_markers=[...], and empty_group_marker=18446744073709551615.