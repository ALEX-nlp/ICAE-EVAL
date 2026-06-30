## Product Requirement Document

# Graph Data Structures and Algorithms - Mutable Graph Modeling and Analysis

## Project Goal

Build a graph data structure and algorithm library that allows developers to create mutable directed, undirected, keyed, stable-indexed, and disjoint-set structures without hand-writing adjacency management or common graph algorithms.

---

## Background & Problem

Without this library, developers are forced to manually maintain node identifiers, adjacency lists, edge weights, traversal queues, shortest-path state, component bookkeeping, and disjoint-set representatives. This leads to repetitive code, edge-case bugs around removals and duplicate edges, and inconsistent algorithm behavior across projects.

With this library, developers can create graph structures suited to their identifier and mutation needs, then run standard algorithms through a compact interface that returns deterministic, inspectable results.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. 
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository. 
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Mutable Undirected Graph Structure

**As a developer, I want to build an undirected graph with node removal, self-loops, and repeated connections, so I can model mutable relationships without losing adjacency correctness.**

**Expected Behavior / Usage:**

A graph accepts node values and weighted connections. In undirected mode, an edge can be found from either endpoint, self-loops are valid, and repeated connections remain distinct. Removing a node removes every incident connection while preserving unrelated edges and neighbor lists.

**Test Cases:** `rcb_tests/public_test_cases/feature1_undirected_graph_mutation.json`

```json
{
    "description": "Undirected graph adjacency, self-loop, parallel edge, and node removal behavior.",
    "cases": [
        {
            "input": {
                "feature": "undirected_mutation",
                "graph_kind": "undirected",
                "scenario": "remove a node after adding reciprocal, self-loop, and parallel connections"
            },
            "expected_output": "before_nodes=4\nbefore_edges=7\nbefore_has_a_b=yes\nbefore_has_d_a=yes\nbefore_has_a_a=yes\nbefore_neighbors_of_b=[0, 2, 0]\nafter_nodes=3\nafter_edges=1\nafter_has_a_b=no\nafter_has_d_a=no\nafter_has_a_a=no\nafter_has_b_c=yes\nafter_neighbors_of_b=[2]\n"
        }
    ]
}
```

---

### Feature 2: Edge Replacement Semantics

**As a developer, I want edge updates to replace the existing connection for the relevant endpoint pair, so I can update weights without accidentally creating duplicate edges.**

**Expected Behavior / Usage:**

When an update targets the same ordered pair in a directed graph, the existing edge is reused and its value is replaced. In an undirected graph, updating the reverse endpoint order also reuses the same connection. The output reports edge counts, whether the edge identity was reused, and the final stored weights.

**Test Cases:** `rcb_tests/public_test_cases/feature2_edge_update.json`

```json
{
    "description": "Updating an existing edge reuses the edge slot in the relevant direction instead of creating a duplicate.",
    "cases": [
        {
            "input": {
                "feature": "update_edge",
                "scenario": "compare directed forward updates with undirected reverse-endpoint updates"
            },
            "expected_output": "directed_edges=2\ndirected_reused_forward_id=yes\ndirected_forward_weight=2\nundirected_edges=1\nundirected_reused_reverse_id=yes\nundirected_edge_weight=2\n"
        }
    ]
}
```

---

### Feature 3: Graph Algorithms

**As a developer, I want standard graph algorithms for traversal, pathfinding, cycle detection, and spanning forests, so I can analyze graph structure without implementing these algorithms manually.**

**Expected Behavior / Usage:**

*3.1 Traversal Reachability — Depth-first and breadth-first walks report reachable nodes in directed graphs and in reversed graph views.*

Traversal starts from a named node and visits only nodes reachable from that start. The same graph can be viewed with all directions reversed; in that view, reachability changes while the node set is unchanged. The output includes traversal type, reachable counts, a concrete visit order from the main start, and reversed-view counts.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_traversal_reachability.json`

```json
{
    "description": "Traversal reports the reachable portion of a directed graph and can traverse the reversed view.",
    "cases": [
        {
            "input": {
                "feature": "traversal_counts",
                "walk": "depth_first",
                "scenario": "reachable counts from several starts including the reversed graph view"
            },
            "expected_output": "walk=depth_first\nfrom_H_count=4\nfrom_H_order=[\"H\", \"I\", \"K\", \"J\"]\nfrom_I_count=3\nreverse_from_H_count=1\nreverse_from_K_count=3\n"
        },
        {
            "input": {
                "feature": "traversal_counts",
                "walk": "breadth_first",
                "scenario": "reachable counts and visit order from the same graph"
            },
            "expected_output": "walk=breadth_first\nfrom_H_count=4\nfrom_H_order=[\"H\", \"J\", \"I\", \"K\"]\nfrom_I_count=3\nreverse_from_H_count=1\nreverse_from_K_count=3\n"
        }
    ]
}
```

---

*3.2 Weighted Shortest Paths — Weighted path algorithms report distances, paths, and unreachable targets.*

For nonnegative weighted graphs, shortest-path queries return exact total costs. A full-source query reports all reachable node distances, a target-limited query reports the selected target distance, a zero-heuristic best-first route matches the shortest directed route, and a coordinate heuristic route reports the selected path through coordinates. If a directed target cannot be reached, the output contains an explicit no-path signal.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_shortest_paths.json`

```json
{
    "description": "Shortest path algorithms return path costs, reachable labels, and no-path signals for weighted graphs.",
    "cases": [
        {
            "input": {
                "feature": "shortest_paths",
                "algorithm": "dijkstra",
                "scenario": "all shortest distances and one target-limited query in an undirected weighted graph"
            },
            "expected_output": "algorithm=dijkstra\ndistances=A:0,B:7,C:9,D:11,E:20,F:20\ntarget_C_distance=9\n"
        },
        {
            "input": {
                "feature": "shortest_paths",
                "algorithm": "astar_zero",
                "scenario": "zero heuristic route and unreachable reverse route in a directed weighted graph"
            },
            "expected_output": "algorithm=astar_zero\nA_to_E_cost=23\nA_to_E_path=[\"A\", \"D\", \"E\"]\nE_to_B_reachable=no\n"
        },
        {
            "input": {
                "feature": "shortest_paths",
                "algorithm": "astar_manhattan",
                "scenario": "coordinate heuristic route in a weighted directed graph"
            },
            "expected_output": "algorithm=astar_manhattan\nstart_to_goal_cost=6\nstart_to_goal_path=(0,0)->(0,2)->(3,3)->(4,2)\n"
        }
    ]
}
```

---

*3.3 Undirected Cycle Detection — Cycle detection distinguishes acyclic trees from cycle-forming additions.*

An undirected graph with no edges or only tree edges is acyclic. Adding a self-loop, adding an edge that closes a triangle, or adding an edge that closes a longer path creates a cycle. Removing those cycle-forming edges restores the acyclic state when no other cycle remains.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_undirected_cycle_detection.json`

```json
{
    "description": "Undirected cycle detection distinguishes trees from self-loops, triangle closures, and longer cycle closures.",
    "cases": [
        {
            "input": {
                "feature": "cycle_detection",
                "scenario": "add and remove cycle-forming edges while observing cycle presence"
            },
            "expected_output": "initial=no\nafter_tree_edges=no\nwith_self_loop=yes\nafter_self_loop_removed=no\nwith_triangle_edge=yes\nafter_triangle_removed=no\nafter_path_extension=no\nafter_closing_long_cycle=yes\n"
        }
    ]
}
```

---

*3.4 Minimum Spanning Forest — Weighted disconnected graphs produce a minimum forest per component.*

For a weighted graph with multiple connected components, the spanning result keeps every node and chooses a minimum set of edges inside each component. The edge count equals the node count minus the number of connected components, and heavier alternatives between already connected nodes are excluded.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_minimum_spanning_forest.json`

```json
{
    "description": "A minimum spanning forest keeps all nodes, selects minimum connecting edges per component, and rejects heavier alternatives.",
    "cases": [
        {
            "input": {
                "feature": "minimum_spanning_forest",
                "scenario": "two-component weighted graph with exact selected and rejected edges"
            },
            "expected_output": "nodes=10\nedges=8\nselected_edges=A-B,A-D,B-E,E-C,E-G,D-F,H-I,I-J\nrejected_D_B=yes\nrejected_B_C=yes\n"
        }
    ]
}
```

---

### Feature 4: Keyed Graphs

**As a developer, I want graphs keyed directly by node values, so I can work with externally meaningful identifiers without first managing numeric indices.**

**Expected Behavior / Usage:**

*4.1 Keyed Weighted Graph — Value-keyed undirected graphs replace duplicate edge weights and support weighted distances.*

A keyed undirected graph stores nodes by their values. Adding the same undirected endpoint pair again returns the previous edge value and replaces it with the new one. Weighted shortest-path distances then use the updated edge values.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_keyed_weighted_graph.json`

```json
{
    "description": "A keyed undirected graph stores nodes by value, replaces duplicate edge weights, and supports weighted distances.",
    "cases": [
        {
            "input": {
                "feature": "graphmap_weighted",
                "graph_kind": "keyed undirected weighted",
                "scenario": "insert weighted edges, replace duplicates, then compute distances"
            },
            "expected_output": "nodes=6\nedges=9\nfirst_E_F_was_new=yes\nold_F_B_weight=15\nold_F_E_weight=5\ncurrent_E_F_weight=6\ndistances=A:0,B:7,C:9,D:11,E:20,F:20\n"
        }
    ]
}
```

---

*4.2 Keyed Edge Removal — Edge removal follows directed or undirected orientation rules.*

In an undirected keyed graph, removing an edge using reverse endpoint order removes the connection. In a directed keyed graph, a reverse-order removal does not remove the forward edge; only the exact forward endpoint order removes it. Missing edge removals return a missing signal.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_keyed_edge_removal.json`

```json
{
    "description": "Removing keyed graph edges respects whether the graph is undirected or directed.",
    "cases": [
        {
            "input": {
                "feature": "graphmap_removal",
                "direction": "undirected",
                "scenario": "remove an undirected edge using reverse endpoint order"
            },
            "expected_output": "direction=undirected\nbefore_1_to_2=-1\nbefore_2_to_1=-1\nbefore_neighbors_of_1=1\nremove_missing=missing\nremove_existing_reverse=-1\nafter_edges=0\nafter_1_to_2=missing\nafter_2_to_1=missing\nafter_neighbors_of_1=0\n"
        },
        {
            "input": {
                "feature": "graphmap_removal",
                "direction": "directed",
                "scenario": "attempt reverse removal before removing the directed edge in forward order"
            },
            "expected_output": "direction=directed\nbefore_1_to_2=-1\nbefore_2_to_1=missing\nbefore_neighbors_of_1=1\nremove_missing=missing\nremove_reverse=missing\nremove_forward=-1\nafter_edges=0\nafter_1_to_2=missing\nafter_2_to_1=missing\nafter_neighbors_of_1=0\n"
        }
    ]
}
```

---

*4.3 Keyed Components and Indexed Conversion — Keyed directed graphs expose components and can be converted to indexed form.*

A keyed directed graph reports strongly connected components as groups of node values. Converting the same graph to an indexed representation preserves the number of nodes and edges so later algorithms can operate on index-based storage without losing graph structure.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_keyed_components_and_conversion.json`

```json
{
    "description": "A keyed directed graph can report strongly connected components and convert to an indexed graph without losing edge weights.",
    "cases": [
        {
            "input": {
                "feature": "graphmap_components",
                "scenario": "compute components and convert the keyed graph to indexed form"
            },
            "expected_output": "sccs=[[0, 3, 6], [1, 4, 7], [2, 5, 8]]\nconverted_nodes=9\nconverted_edges=11\n"
        }
    ]
}
```

---

### Feature 5: Stable Indexed Graphs

**As a developer, I want indexed graphs whose identifiers remain stable after removals, so I can keep external references without compacting indices unexpectedly.**

**Expected Behavior / Usage:**

*5.1 Stable Indices and Vacancies — Removed nodes create holes while bounds and reusable vacancies remain observable.*

A stable indexed graph keeps surviving node identifiers unchanged after removals. The maximum occupied-or-vacant bound can remain larger than the live node count until the graph is cleared. Clearing edges removes all connections without removing nodes, and later node insertion can reuse vacant identifiers.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_stable_indices_and_vacancies.json`

```json
{
    "description": "A stable indexed graph preserves index holes, reports bounds separately from counts, and reuses vacancies.",
    "cases": [
        {
            "input": {
                "feature": "stable_indices",
                "scenario": "remove nodes, clear edges, and observe remaining indices and reused vacancies"
            },
            "expected_output": "remaining_node_indices=[0, 2]\nnode_bound_full=10\nnode_bound_after_removals=10\nnode_bound_after_clear=0\n[a specific sentinel error code — ask the PM for the exact string]=[1,9]\nedge_count_after_clear_edges=0\n"
        }
    ]
}
```

---

*5.2 Stable Strong Components — Component algorithms ignore removed-node holes but preserve stable identifiers.*

Strongly connected component analysis on a stable directed graph returns groups of existing node identifiers. Removed identifiers do not appear, while replacement nodes use their stable identifiers and participate in the correct component. Both supported component algorithms produce the same component grouping for the tested graph.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_stable_strong_components.json`

```json
{
    "description": "Strongly connected component algorithms work on stable indexed directed graphs with removed nodes.",
    "cases": [
        {
            "input": {
                "feature": "stable_scc",
                "algorithm": "kosaraju",
                "scenario": "component groups after replacing and removing one node"
            },
            "expected_output": "algorithm=kosaraju\ncomponents=[[0, 3, 6], [1, 7, 9], [2, 5, 8]]\n"
        },
        {
            "input": {
                "feature": "stable_scc",
                "algorithm": "tarjan",
                "scenario": "component groups after replacing and removing one node"
            },
            "expected_output": "algorithm=tarjan\ncomponents=[[0, 3, 6], [1, 7, 9], [2, 5, 8]]\n"
        }
    ]
}
```

---

*5.3 Stable DOT Output — Stable graphs render labeled nodes and directed labeled edges in DOT text.*

Rendering a stable directed graph as DOT emits a `digraph` block with one line for each node label and one line for each labeled edge. Self-loops are rendered as edges from a node to itself, and ordinary directed edges are rendered with source and target identifiers.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_stable_dot_output.json`

```json
{
    "description": "A stable indexed graph renders node labels, self-loops, and directed edges in DOT text.",
    "cases": [
        {
            "input": {
                "feature": "stable_dot",
                "format": "dot",
                "scenario": "two labeled nodes with one self-loop and one directed edge"
            },
            "expected_output": "digraph {\n    0 [label=\"x\"]\n    1 [label=\"y\"]\n    0 -> 0 [label=\"10\"]\n    0 -> 1 [label=\"20\"]\n}\n"
        }
    ]
}
```

---

*5.4 Invalid Stable Endpoint Errors — Adding an edge to a missing stable identifier is normalized.*

If an edge is added to an endpoint identifier that is vacant because it was removed, or to an identifier outside the current graph bound, the adapter reports a language-neutral invalid graph reference error. The stdout must not expose runtime exception class names or host-language runtime failure messages.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_stable_invalid_endpoint_errors.json`

```json
{
    "description": "Adding an edge to a missing stable index is reported as a normalized invalid-reference error.",
    "cases": [
        {
            "input": {
                "feature": "stable_invalid_edge",
                "invalid_endpoint": "vacant",
                "scenario": "target index was previously removed"
            },
            "expected_output": "error=invalid_graph_reference\n"
        },
        {
            "input": {
                "feature": "stable_invalid_edge",
                "invalid_endpoint": "out_of_bounds",
                "scenario": "target index is beyond the current graph bound"
            },
            "expected_output": "error=invalid_graph_reference\n"
        }
    ]
}
```

---

### Feature 6: Disjoint-Set Union

**As a developer, I want disjoint-set union operations, so I can merge equivalence classes and query connected representatives efficiently.**

**Expected Behavior / Usage:**

A disjoint-set structure initially gives each element its own representative. Unioning an element with itself reports no new merge. Unioning elements from different sets merges them, causes members to share representatives, and reduces the number of disjoint sets. Converting a fully connected larger structure into labels yields a single label class.

**Test Cases:** `rcb_tests/public_test_cases/feature6_disjoint_set_union.json`

```json
{
    "description": "Disjoint-set union reports initial representatives, merge relationships, set counts, and full labeling collapse.",
    "cases": [
        {
            "input": {
                "feature": "union_find",
                "scenario": "merge several sets and convert a larger connected structure into labels"
            },
            "expected_output": "initial_roots=0:0:yes,1:1:yes,2:2:yes,3:3:yes,4:4:yes,5:5:yes,6:6:yes,7:7:yes\nsame_0_1=yes\nsame_0_3=yes\nsame_1_3=yes\ndifferent_0_2=yes\nsame_7_0=yes\nsame_6_5=yes\ndifferent_6_7=yes\nset_count=3\nlabeling_single_component=yes\n"
        }
    ]
}
```

---

### Feature 7: Graph Isomorphism

**As a developer, I want graph isomorphism checks, so I can compare graph structure independently from concrete node identifiers and optionally require matching weights.**

**Expected Behavior / Usage:**

*7.1 Structure-Only Isomorphism — Structural equivalence changes as nodes and edges are added.*

Two graphs are isomorphic when their directed structure can be matched by renaming nodes. Equal empty graphs, equal node counts, and differently named but structurally identical edge patterns are accepted. A node count mismatch or an edge present on only one side is rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_graph_isomorphism.json`

```json
{
    "description": "Graph isomorphism depends on structure rather than concrete node names and changes as nodes or edges are added.",
    "cases": [
        {
            "input": {
                "feature": "isomorphism",
                "scenario": "incremental",
                "graph_pair": "incrementally add equal and unequal node or edge structure"
            },
            "expected_output": "scenario=incremental\nempty=yes\none_node_each=yes\ntwo_nodes_each=yes\nextra_node_left=no\nthree_nodes_each=yes\nedge_left_only=no\nmatching_edges=yes\n"
        },
        {
            "input": {
                "feature": "isomorphism",
                "scenario": "renamed_shape",
                "graph_pair": "same directed shape with renamed nodes and mirrored construction order"
            },
            "expected_output": "scenario=renamed_shape\none_edge=yes\ntwo_edges=yes\nthree_cycle=yes\nafter_two_isolated_nodes=yes\nafter_renamed_tail=yes\n"
        }
    ]
}
```

---

*7.2 Weight-Sensitive Isomorphism — Custom matching rejects structurally equal graphs with changed edge weights.*

When edge values are part of the matching contract, two otherwise identical graphs are not considered equivalent if a corresponding edge value differs. The output reports the result after changing different individual edge weights.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_weight_sensitive_isomorphism.json`

```json
{
    "description": "Weighted isomorphism with custom matching rejects graphs whose edge weights differ.",
    "cases": [
        {
            "input": {
                "feature": "isomorphism_matching",
                "scenario": "change individual edge weights while requiring equal node and edge weights"
            },
            "expected_output": "edge0_weight_changed=no\nedge1_weight_changed=no\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_undirected_graph_mutation.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_undirected_graph_mutation@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the standard traversal naming conventions used in the connectivity module
- use the same naming prefix for the component identifiers as defined in the strong_connectivity utility
