## Product Requirement Document

# Graph Algorithms Toolkit - Standardized Path, Graph, Grid, Matrix, Flow, and Assignment Contracts

## Project Goal

Build a graph algorithms and data-structure toolkit that allows developers to solve routing, connectivity, grid, matrix transformation, network flow, assignment optimization, and numeric helper tasks without rewriting common algorithmic building blocks.

---

## Background & Problem

Without this library/tool, developers are forced to hand-code shortest-path search, component grouping, matrix manipulation, flow augmentation, and assignment matching for each project. This leads to repetitive code, edge-case bugs, inconsistent output handling, and hard-to-maintain algorithm implementations.

With this library/tool, developers can provide graph, grid, matrix, or numeric inputs through a focused execution adapter and receive deterministic, inspectable stdout describing the externally visible result of each supported operation.

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

### Feature 1: Route Search

**As a developer**, I want to search graphs and maze-like spaces with multiple route strategies, so I can obtain reachable paths, costs, and cycle information for weighted and unweighted problems.

**Expected Behavior / Usage:**

*1.1 Weighted Shortest Paths — Computes a minimum-cost route on a directed weighted graph.*

Input selects weighted shortest-path routing and a goal node. Output reports `found=true` with the ordered node path and total cost when reachable, or `found=false` when no route exists. The path includes both start and goal nodes.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_weighted_shortest_paths.json`

```json
{
    "description": "Compute shortest routes on a directed weighted graph and report whether a goal is reachable, the selected node path, and the total travel cost.",
    "cases": [
        {
            "input": {"feature": "weighted_shortest_path", "scenario": "least_total_cost", "goal": "0"},
            "expected_output": "found=true\npath=[1,0]\ncost=8\n"
        },
        {
            "input": {"feature": "weighted_shortest_path", "scenario": "least_total_cost", "goal": "2"},
            "expected_output": "found=true\npath=[1,6,2]\ncost=12\n"
        }
    ]
}
```

*1.2 Weighted Maze Routes — Computes costed routes through blocked cells.*

Input selects weighted maze routing, a strategy, and a goal coordinate. Output reports reachability, path length, total cost, and whether every returned step lies on an open cell.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_weighted_maze_routes.json`

```json
{
    "description": "Find weighted routes through a blocked rectangular maze and report reachability, route length, cost, and whether every returned step is on an open cell.",
    "cases": [
        {"input": {"feature": "maze_weighted_path", "scenario": "estimated_cost", "goal_x": "6", "goal_y": "3"}, "expected_output": "found=true\npath_length=9\ncost=8\nall_steps_open=true\n"},
        {"input": {"feature": "maze_weighted_path", "scenario": "iterative_estimated_cost", "goal_x": "6", "goal_y": "3"}, "expected_output": "found=true\npath_length=9\ncost=8\nall_steps_open=true\n"}
    ]
}
```

*1.3 Unweighted Maze Routes — Computes step-count routes through blocked cells.*

Input selects unweighted maze routing, a strategy, and a goal coordinate. Output reports reachability, path length, and whether every step lies on an open cell.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_unweighted_maze_routes.json`

```json
{
    "description": "Find unweighted routes through a blocked rectangular maze and report reachability, route length, and whether every returned step is on an open cell.",
    "cases": [
        {"input": {"feature": "maze_unweighted_path", "scenario": "fewest_steps", "goal_x": "6", "goal_y": "3"}, "expected_output": "found=true\npath_length=9\nall_steps_open=true\n"},
        {"input": {"feature": "maze_unweighted_path", "scenario": "iterative_depth", "goal_x": "6", "goal_y": "3"}, "expected_output": "found=true\npath_length=9\nall_steps_open=true\n"}
    ]
}
```

*1.4 All Optimal Routes — Enumerates equal-cost optimal solutions.*

Input selects a graph scenario with multiple equally optimal routes. Output reports the shared cost, number of optimal paths, and concrete path list when the scenario enumerates paths.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_all_optimal_routes.json`

```json
{
    "description": "Enumerate all equally optimal routes in graphs with multiple optimal solutions and report the common cost and route count or route list.",
    "cases": [
        {"input": {"feature": "optimal_route_set", "scenario": "multiple_goals"}, "expected_output": "found=true\ncost=4\npath_count=4\npaths=[[1,2,4]|[1,2,5,6,7]|[1,3,4]|[1,3,5,6,7]]\n"}
    ]
}
```

*1.5 Cycle Detection — Finds a reachable directed cycle.*

Input supplies a start node. Output reports whether a cycle is reachable and, when found, prints the closed cycle path and its node count.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_cycle_detection.json`

```json
{
    "description": "Detect the first reachable directed cycle from a start node and report the closed cycle path when one exists.",
    "cases": [
        {"input": {"feature": "cycle_detection", "start": "0"}, "expected_output": "found=true\ncycle=[0,1,0]\ncycle_length=3\n"},
        {"input": {"feature": "cycle_detection", "start": "2"}, "expected_output": "found=true\ncycle=[2,5,1,0,2]\ncycle_length=5\n"}
    ]
}
```

*1.6 Geographic Route — Routes between named geographic points.*

Input selects the city-routing scenario. Output reports the city sequence, total rounded distance, and whether alternative weighted search strategies agree on the cost.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_geographic_route.json`

```json
{
    "description": "Route between named geographic points using weighted road distances and report the selected city sequence and total distance consistency.",
    "cases": [
        {"input": {"feature": "gps_route", "scenario": "city_route"}, "expected_output": "path=[Paris,Lyon,Marseille,Cannes]\ncost=804971\ncosts_match=true\n"}
    ]
}
```

---

### Feature 2: Rectangular Grid Operations

**As a developer**, I want to model active cells in a rectangular grid, so I can query occupancy, neighbors, borders, and adjacency edges.

**Expected Behavior / Usage:**

Input selects a grid scenario. Output reports only externally visible grid state: active vertex counts, emptiness/fullness, changed flags for mutating operations, coordinate lists for neighbors, and edge lists for adjacency enumeration. Coordinate lists use `x,y` entries separated by `|`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_grid_operations.json`

```json
{
    "description": "Maintain a rectangular set of active cells and report state changes for emptiness, neighbor modes, borders, and edge enumeration.",
    "cases": [
        {"input": {"feature": "grid", "scenario": "empty"}, "expected_output": "vertices=0\nis_empty=true\nis_full=true\nedges=0\nclear_changed=false\nfill_changed=false\nafter_invert_vertices=0\n"},
        {"input": {"feature": "grid", "scenario": "diagonal_mode"}, "expected_output": "cardinal=[[a specific coordinate string format using pipe separators (ask implementation details)]]\ndiagonal=[0,0|0,1|0,2|1,0|1,2|2,0|2,1|2,2]\nrestored=[[a specific coordinate string format using pipe separators (ask implementation details)]]\n"}
    ]
}
```

---

### Feature 3: Matrix Operations

**As a developer**, I want row-major matrix construction and transformations, so I can inspect dimensions and flattened contents after common operations.

**Expected Behavior / Usage:**

Input selects a matrix scenario. Output reports dimensions and flattened row-major arrays for construction, fill, rotation, flipping, transposition, slicing, and normalized invalid-shape errors.

**Test Cases:** `rcb_tests/public_test_cases/feature3_matrix_operations.json`

```json
{
    "description": "Create and transform row-major matrices, reporting dimensions and flattened contents after updates, rotations, flips, transposition, slicing, or invalid shape detection.",
    "cases": [
        {"input": {"feature": "matrix", "scenario": "construct_fill"}, "expected_output": "rows=2\ncolumns=2\nbefore=[0,2,10,11]\nafter=[33,33,33,33]\n"},
        {"input": {"feature": "matrix", "scenario": "rotate"}, "expected_output": "cw_1=[6,3,0,7,4,1,8,5,2]\ncw_2=[8,7,6,5,4,3,2,1,0]\nccw_1=[2,5,8,1,4,7,0,3,6]\n"}
    ]
}
```

---

### Feature 4: Undirected Connected Components

**As a developer**, I want to group overlapping undirected node sets, so I can identify connected memberships and empty groups.

**Expected Behavior / Usage:**

Input selects an undirected component scenario. Output reports component counts and sorted memberships, or group markers for original input groups. Empty groups are represented with a sentinel marker value.

**Test Cases:** `rcb_tests/public_test_cases/feature4_undirected_components.json`

```json
{
    "description": "Group overlapping undirected node sets into connected components and report component memberships or group markers.",
    "cases": [
        {"input": {"feature": "components", "scenario": "group_lists"}, "expected_output": "component_count=2\ncomponents=[[1,2,3,4,7]|[5,6]]\n"},
        {"input": {"feature": "components", "scenario": "separate_with_empty"}, "expected_output": "element_count=4\ngroup_markers=[1,1,[a specific large unsigned sentinel integer (keep reference to code for value)],1]\nempty_group_marker=[a specific large unsigned sentinel integer (keep reference to code for value)]\n"}
    ]
}
```

---

### Feature 5: Directed Strongly Connected Components

**As a developer**, I want to partition directed graphs into mutually reachable groups, so I can reason about cycles and graph condensation.

**Expected Behavior / Usage:**

Input selects whether to inspect all components, components reachable from a start node, an individual node's component, or externally discovered successors. Output reports sorted component memberships and component counts.

**Test Cases:** `rcb_tests/public_test_cases/feature5_strong_components.json`

```json
{
    "description": "Partition directed graphs into strongly connected components and report complete, reachable, individual, and externally discovered components.",
    "cases": [
        {"input": {"feature": "strong_components", "scenario": "all"}, "expected_output": "component_count=6\ncomponents=[[0,1,2,3,4]|[5]|[6,7,8]|[9,10,11,12]|[13,14]|[15]]\n"},
        {"input": {"feature": "strong_components", "scenario": "from_start"}, "expected_output": "component_count=4\ncomponent_heads=[5,6,13,15]\ncomponents=[[5]|[6,7,8]|[13,14]|[15]]\n"}
    ]
}
```

---

### Feature 6: Topological Ordering

**As a developer**, I want to order acyclic directed dependencies, so I can process prerequisites before dependents.

**Expected Behavior / Usage:**

Input selects a topological-order scenario. Output reports the resulting ordered sequence. Empty input returns an empty sequence.

**Test Cases:** `rcb_tests/public_test_cases/feature6_topological_order.json`

```json
{
    "description": "Topologically order directed acyclic dependencies and report the resulting sequence.",
    "cases": [
        {"input": {"feature": "topological_order", "scenario": "empty"}, "expected_output": "result=[]\n"}
    ]
}
```

---

### Feature 7: Maximum Flow

**As a developer**, I want to compute maximum flow through capacity networks, so I can inspect total throughput and edge-level positive flows.

**Expected Behavior / Usage:**

Input selects a capacity-network scenario. Output reports `max_flow` and positive `from>to:flow` entries, or incremental totals for updates, disconnected totals, or language-neutral endpoint errors.

**Test Cases:** `rcb_tests/public_test_cases/feature7_max_flow.json`

```json
{
    "description": "Compute maximum directed flow through capacity networks and report total flow, edge flows, incremental update totals, disconnected totals, or normalized endpoint errors.",
    "cases": [
        {"input": {"feature": "max_flow", "scenario": "network_dense"}, "expected_output": "max_flow=5\nflows=[A>B:2,A>D:3,B>C:2,C>D:1,C>E:1,D>F:4,E>G:1,F>G:4]\n"},
        {"input": {"feature": "max_flow", "scenario": "network_sparse"}, "expected_output": "max_flow=5\nflows=[A>B:2,A>D:3,B>C:2,C>D:1,C>E:1,D>F:4,E>G:1,F>G:4]\n"}
    ]
}
```

---

### Feature 8: Assignment Optimization

**As a developer**, I want to solve maximum and minimum assignment matrices, so I can obtain an optimum total and selected column for each row.

**Expected Behavior / Usage:**

Input selects an assignment scenario. Output reports the optimum total and, when relevant, row-to-column assignments as a zero-based array. Invalid unbalanced input must be normalized to `error=unbalanced_assignment_matrix`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_assignment_optimization.json`

```json
{
    "description": "Solve assignment optimization matrices and report optimum total, selected columns, empty results, or normalized unbalanced-matrix errors.",
    "cases": [
        {"input": {"feature": "assignment", "scenario": "maximize_small"}, "expected_output": "total=10\nassignments=[2,0,1]\n"},
        {"input": {"feature": "assignment", "scenario": "minimize_cranes"}, "expected_output": "total=275\n"}
    ]
}
```

---

### Feature 9: Numeric Absolute Difference

**As a developer**, I want a numeric helper for absolute differences, so I can compare values without caring about operand order.

**Expected Behavior / Usage:**

Input selects the absolute-difference scenario. Output reports forward and reverse differences for signed, unsigned, and floating-point values.

**Test Cases:** `rcb_tests/public_test_cases/feature9_numeric_helpers.json`

```json
{
    "description": "Calculate absolute differences for signed, unsigned, and floating-point numeric values independent of operand order.",
    "cases": [
        {"input": {"feature": "numeric", "scenario": "absolute_difference"}, "expected_output": "signed_forward=1\nsigned_reverse=1\nunsigned_forward=1\nunsigned_reverse=1\nfloat_forward=1.0\nfloat_reverse=1.0\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the flow notation used in the graph module
- adhere to the global output standardization protocol
