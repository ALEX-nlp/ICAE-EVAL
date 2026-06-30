## Product Requirement Document

# Graph Toolkit — Standardized Input/Output Specification

## Project Goal

Build a command-driven graph computation service. The program reads a single
self-contained command from standard input that describes a graph and one
operation to perform on it, then writes the result to standard output in a
fixed, deterministic, line-oriented text format. The goal is a precise,
language-neutral contract for graph construction, inspection, mutation, and a
family of classic graph algorithms (traversal, connectivity, shortest paths,
spanning trees, ordering, and coloring), such that the same input always
produces the same output regardless of internal data-structure choices.

## Background & Problem

Graph algorithms are a common building block, but their results are easy to get
wrong and hard to compare across implementations: iteration order over vertices
and edges is often unspecified, several correct answers may exist (multiple
valid topological orders, equally-weighted spanning trees, alternate greedy
colorings), and error reporting differs wildly between runtimes. Consumers need
a single, well-defined surface where:

- a graph is described purely by data (a list of vertex values and a list of
  weighted edges given as index pairs), with no reference to any host language;
- every operation has one canonical textual answer, with all
  internally-unspecified ordering canonicalized (sorted) before output;
- error conditions are surfaced as stable, neutral categories rather than
  runtime-specific exception text.

This specification defines that surface and the exact output for each operation.

## Architecture & Engineering Constraints

**Invocation.** The program reads exactly one JSON object from stdin and writes
plain text to stdout. It performs one operation per run.

**Common input fields.**
- `op` (string): the operation to perform (see Core Features).
- `directed` (bool): whether the graph is directed (`true`) or undirected
  (`false`).
- `vertices` (array of integers): vertex values. The vertex at array position
  `k` is assigned the integer id `k` (ids are `0..N-1` in array order). Edge
  endpoints and all query fields refer to these ids.
- `edges` (array of `[from, to, weight]` triples): each edge connects vertex id
  `from` to vertex id `to` with an integer `weight`. For undirected graphs an
  edge is symmetric.
- Operation-specific fields (`vertex`, `from`, `to`, `start`, `end`, `source`,
  `target`, `queries`, `extra_edge`) are described per feature.

**Output format.** Output is ASCII text, one item per line, each line
terminated by `\n`. Sequences of ids are rendered as comma-separated ascending
lists. Wherever the underlying computation leaves ordering unspecified (vertex
sets, edge sets, component members, traversed-edge sets), the output is sorted
to a canonical form so it is reproducible. Undirected edges are rendered as
`a--b` with `a <= b`; directed edges as `a->b`.

**Determinism constraint.** Inputs are restricted to instances whose observable
answer is unique under this contract (e.g. chains for ordering, distinct-weight
graphs for spanning trees, forced-chromatic graphs for coloring). The contract
does not promise a specific tie-break among genuinely equivalent solutions.

**Error normalization.** Failure conditions are reported as neutral,
language-agnostic categories on an `error=` line followed by relevant context
lines. No host-language exception names, stack traces, or runtime message
suffixes appear in output. The defined categories are: `vertex_not_found`,
`edge_not_found`, `vertices_not_found`, `negative_edge_weight`,
`negative_cycle`, plus `requires_directed` / `requires_undirected` when an
operation is applied to the wrong graph orientation.

## Core Features

### Feature 1: Graph summary

`op=summary`. Report whether the graph is directed and its vertex and edge
counts.

Input: `{"op":"summary","directed":true,"vertices":[10,20,30],"edges":[[0,1,5],[1,2,7]]}`
Output:
```
directed=true
vertex_count=3
edge_count=2
```

Input: `{"op":"summary","directed":false,"vertices":[0,1,2],"edges":[[0,1,1],[1,2,1]]}`
Output:
```
directed=false
vertex_count=3
edge_count=2
```

### Feature 2: Neighbor lookup

`op=neighbors`, field `vertex`. List the adjacent vertices of `vertex`
(outgoing side for directed graphs) in ascending order.

Input: `{"op":"neighbors","directed":true,"vertex":0,"vertices":[0,1,2,3],"edges":[[0,2,1],[0,1,1],[0,3,1]]}`
Output:
```
vertex=0
neighbors=1,2,3
```

Input: `{"op":"neighbors","directed":false,"vertex":1,"vertices":[0,1,2],"edges":[[0,1,1],[1,2,1]]}`
Output:
```
vertex=1
neighbors=0,2
```

### Feature 3: Edge existence

`op=edge_existence`, field `queries` (array of `[from,to]` pairs). For each
query report whether that directed edge is `present` or `absent`. In an
undirected graph the relation is symmetric.

Input: `{"op":"edge_existence","directed":true,"queries":[[0,1],[1,0],[1,2]],"vertices":[0,1,2],"edges":[[0,1,1],[1,2,1]]}`
Output:
```
0->1=present
1->0=absent
1->2=present
```

Input: `{"op":"edge_existence","directed":false,"queries":[[0,1],[1,0],[0,2]],"vertices":[0,1,2],"edges":[[0,1,1]]}`
Output:
```
0->1=present
1->0=present
0->2=absent
```

### Feature 4: Vertex value lookup

`op=vertex_value`, field `vertex`. Report the stored value of the vertex. An id
with no vertex yields a `vertex_not_found` error.

Input: `{"op":"vertex_value","directed":false,"vertex":1,"vertices":[10,20,30],"edges":[]}`
Output:
```
vertex=1
value=20
```

Input: `{"op":"vertex_value","directed":false,"vertex":9,"vertices":[0,1],"edges":[]}`
Output:
```
error=vertex_not_found
vertex=9
```

### Feature 5: Edge weight lookup

`op=edge_weight`, fields `from`, `to`. Report the weight of the edge between the
two vertices. A missing edge yields an `edge_not_found` error.

Input: `{"op":"edge_weight","directed":false,"from":0,"to":1,"vertices":[0,1],"edges":[[0,1,42]]}`
Output:
```
from=0
to=1
weight=42
```

Input: `{"op":"edge_weight","directed":false,"from":0,"to":1,"vertices":[0,1],"edges":[]}`
Output:
```
error=edge_not_found
from=0
to=1
```

### Feature 6: Remove vertex

`op=remove_vertex`, field `target`. Remove the vertex and all incident edges,
then report the resulting graph: counts, the sorted surviving vertex ids, and
the sorted surviving edges.

Input: `{"op":"remove_vertex","directed":false,"target":1,"vertices":[0,1,2],"edges":[[0,1,1],[1,2,1],[0,2,1]]}`
Output:
```
vertex_count=2
edge_count=1
vertices=0,2
edges=0--2
```

### Feature 7: Remove edge

`op=remove_edge`, fields `from`, `to`. Remove the single edge between the two
vertices, then report the resulting graph contents.

Input: `{"op":"remove_edge","directed":false,"from":0,"to":1,"vertices":[0,1,2],"edges":[[0,1,1],[1,2,1]]}`
Output:
```
vertex_count=3
edge_count=1
vertices=0,1,2
edges=1--2
```

### Feature 8: Guarded edge insertion

`op=add_edge_invalid`, field `extra_edge` (`[from,to,weight]`). Attempt to add
the edge. If either endpoint does not exist it is rejected with a
`vertices_not_found` error; otherwise it is accepted.

Input: `{"op":"add_edge_invalid","directed":false,"extra_edge":[0,5,1],"vertices":[0,1],"edges":[]}`
Output:
```
error=vertices_not_found
vertex_lhs=0
vertex_rhs=5
edge_added=false
```

Input: `{"op":"add_edge_invalid","directed":false,"extra_edge":[0,1,3],"vertices":[0,1],"edges":[]}`
Output:
```
edge_added=true
```

### Feature 9: Degree report

`op=degrees`. For every vertex in ascending order, report out-degree, in-degree
and total degree. For undirected graphs degree counts incident edges.

Input: `{"op":"degrees","directed":true,"vertices":[0,1,2],"edges":[[0,1,1],[0,2,1],[1,2,1]]}`
Output:
```
vertex=0 outdegree=2 indegree=0 degree=2
vertex=1 outdegree=1 indegree=1 degree=2
vertex=2 outdegree=0 indegree=2 degree=2
```

Input: `{"op":"degrees","directed":false,"vertices":[0,1,2],"edges":[[0,1,1],[1,2,1]]}`
Output:
```
vertex=0 outdegree=1 indegree=1 degree=1
vertex=1 outdegree=2 indegree=2 degree=2
vertex=2 outdegree=1 indegree=1 degree=1
```

### Feature 10: Breadth-first traversal

`op=traverse_bfs`, field `start`. Traverse breadth-first from `start` and report
the canonical (sorted) set of edges followed to reach newly discovered vertices,
plus the count.

Input: `{"op":"traverse_bfs","directed":false,"start":0,"vertices":[0,1,2,3],"edges":[[0,1,1],[1,2,1],[2,3,1]]}`
Output:
```
start=0
edge_count=3
traversed_edges=0--1,1--2,2--3
```

### Feature 11: Depth-first traversal

`op=traverse_dfs`, field `start`. Traverse depth-first from `start` and report
the canonical (sorted) set of edges followed to reach newly discovered
vertices, plus the count.

Input: `{"op":"traverse_dfs","directed":true,"start":0,"vertices":[0,1,2,3],"edges":[[0,1,1],[1,2,1],[1,3,1]]}`
Output:
```
start=0
edge_count=3
traversed_edges=0->1,1->2,1->3
```

### Feature 12: Cycle detection

`op=detect_cycle`. Report whether the graph contains a cycle.

Input: `{"op":"detect_cycle","directed":true,"vertices":[0,1,2],"edges":[[0,1,1],[1,2,1]]}`
Output:
```
directed=true
has_cycle=false
```

Input: `{"op":"detect_cycle","directed":true,"vertices":[0,1,2],"edges":[[0,1,1],[1,2,1],[2,0,1]]}`
Output:
```
directed=true
has_cycle=true
```

### Feature 13: Topological ordering

`op=topological_order` (directed graphs). Report whether the graph is acyclic
and, if so, a topological ordering of vertex ids. Inputs are restricted to
graphs with a unique ordering.

Input: `{"op":"topological_order","directed":true,"vertices":[0,1,2,3],"edges":[[0,1,1],[1,2,1],[2,3,1]]}`
Output:
```
acyclic=true
order=0,1,2,3
```

Input: `{"op":"topological_order","directed":true,"vertices":[0,1,2],"edges":[[0,1,1],[1,2,1],[2,0,1]]}`
Output:
```
acyclic=false
```

### Feature 14: Strongly connected components

`op=strongly_connected_components` (directed graphs). Partition into strongly
connected components. Report the component count, then one line per component
listing its sorted members; components are emitted in ascending order.

Input: `{"op":"strongly_connected_components","directed":true,"vertices":[0,1,2,3,4],"edges":[[0,1,1],[1,2,1],[2,0,1],[3,4,1]]}`
Output:
```
count=3
0,1,2
3
4
```

### Feature 15: Unweighted shortest path

`op=shortest_path_unweighted`, fields `start`, `end`. Find a shortest path by
hop count, ignoring weights. Report the path and number of hops, or `path=none`
when unreachable.

Input: `{"op":"shortest_path_unweighted","directed":false,"start":0,"end":3,"vertices":[0,1,2,3],"edges":[[0,1,1],[1,2,1],[2,3,1],[0,3,1]]}`
Output:
```
path=0,3
hops=1
```

Input: `{"op":"shortest_path_unweighted","directed":true,"start":0,"end":2,"vertices":[0,1,2],"edges":[[0,1,1]]}`
Output:
```
path=none
```

### Feature 16: Weighted shortest path

`op=shortest_path_weighted`, fields `start`, `end`. Find a minimum-weight path.
Report the path and total weight, `path=none` when unreachable, or a
`negative_edge_weight` error when the graph contains a negative-weight edge.

Input: `{"op":"shortest_path_weighted","directed":true,"start":0,"end":4,"vertices":[0,1,2,3,4],"edges":[[0,1,3],[1,2,4],[0,2,7],[2,4,2],[0,3,5]]}`
Output:
```
path=0,2,4
weight=9
```

Input: `{"op":"shortest_path_weighted","directed":true,"start":0,"end":2,"vertices":[0,1,2],"edges":[[0,1,1]]}`
Output:
```
path=none
```

Input: `{"op":"shortest_path_weighted","directed":true,"start":0,"end":1,"vertices":[0,1],"edges":[[0,1,-1]]}`
Output:
```
error=negative_edge_weight
from=0
to=1
weight=-1
```

### Feature 17: Single-source shortest paths

`op=single_source_paths`, field `source`. Compute minimum-weight paths from
`source` to every reachable vertex. Report one line per reachable target (in
ascending target order) with its weight and path.

Input: `{"op":"single_source_paths","directed":true,"source":0,"vertices":[0,1,2],"edges":[[0,1,4],[1,2,3]]}`
Output:
```
target=0 weight=0 path=0
target=1 weight=4 path=0,1
target=2 weight=7 path=0,1,2
```

### Feature 18: Negative-aware single-source paths

`op=negative_aware_paths`, field `source`. Compute single-source minimum-weight
paths allowing negative edge weights. Report each target as in Feature 17, or a
`negative_cycle` error when a reachable negative cycle exists.

Input: `{"op":"negative_aware_paths","directed":true,"source":0,"vertices":[0,1,2],"edges":[[0,1,4],[1,2,-2]]}`
Output:
```
target=0 weight=0 path=0
target=1 weight=4 path=0,1
target=2 weight=2 path=0,1,2
```

Input: `{"op":"negative_aware_paths","directed":true,"source":0,"vertices":[0,1,2],"edges":[[0,1,1],[1,2,-3],[2,1,1]]}`
Output:
```
error=negative_cycle
```

### Feature 19: Heuristic-guided path search

`op=heuristic_search`, fields `start`, `target`. Find a minimum-weight path
using a guided search. Report the path and total weight, or a
`negative_edge_weight` error for negative-weight edges.

Input: `{"op":"heuristic_search","directed":true,"start":0,"target":2,"vertices":[0,1,2],"edges":[[0,1,4],[1,2,3],[0,2,9]]}`
Output:
```
path=0,1,2
weight=7
```

Input: `{"op":"heuristic_search","directed":true,"start":0,"target":1,"vertices":[0,1],"edges":[[0,1,-1]]}`
Output:
```
error=negative_edge_weight
from=0
to=1
weight=-1
```

### Feature 20: All-pairs shortest paths

`op=all_pairs_shortest_paths`. Compute the matrix of minimum path weights
between every ordered pair of vertices. Emit one row per source vertex (in id
order) as a comma-separated list; unreachable pairs are `inf`; the diagonal is
`0`.

Input: `{"op":"all_pairs_shortest_paths","directed":true,"vertices":[0,1,2],"edges":[[0,1,4],[1,2,3]]}`
Output:
```
0,4,7
inf,0,3
inf,inf,0
```

### Feature 21: Minimum spanning forest

`op=spanning_forest` (undirected graphs). Compute a minimum spanning forest.
Report the edge count, total weight, and the sorted chosen edges. Inputs use
distinct weights so the forest is unique.

Input: `{"op":"spanning_forest","directed":false,"vertices":[0,1,2,3],"edges":[[0,1,1],[1,2,2],[2,3,3],[0,3,10]]}`
Output:
```
edge_count=3
total_weight=6
0--1
1--2
2--3
```

Input: `{"op":"spanning_forest","directed":false,"vertices":[0,1,2,3],"edges":[[0,1,1],[2,3,2]]}`
Output:
```
edge_count=2
total_weight=3
0--1
2--3
```

### Feature 22: Spanning tree from a root

`op=spanning_tree_from`, field `start` (undirected graphs). Grow a minimum
spanning tree from `start`. Report the tree as in Feature 21, or
`spanning=none` when the graph is not connected from the root.

Input: `{"op":"spanning_tree_from","directed":false,"start":0,"vertices":[0,1,2,3],"edges":[[0,1,1],[1,2,2],[2,3,3],[0,3,10]]}`
Output:
```
edge_count=3
total_weight=6
0--1
1--2
2--3
```

Input: `{"op":"spanning_tree_from","directed":false,"start":0,"vertices":[0,1,2,3],"edges":[[0,1,1],[2,3,2]]}`
Output:
```
spanning=none
```

### Feature 23: Graph coloring

`op=coloring` (undirected graphs). Assign colors so adjacent vertices differ.
Report the vertex count, whether the coloring is proper, and the number of
colors used. Inputs are forced-chromatic so the color count is determined.

Input: `{"op":"coloring","directed":false,"vertices":[0,1,2],"edges":[[0,1,1],[1,2,1],[0,2,1]]}`
Output:
```
vertex_count=3
proper=true
color_count=3
```

Input: `{"op":"coloring","directed":false,"vertices":[0,1],"edges":[[0,1,1]]}`
Output:
```
vertex_count=2
proper=true
color_count=2
```

### Feature 24: DOT export

`op=export_dot`. Serialize the graph to a DOT description. Report the graph kind
(`graph` or `digraph`), then the sorted vertex lines, then the sorted edge
lines. Each vertex line carries its value as a label; each edge line carries its
weight as a label.

Input: `{"op":"export_dot","directed":false,"vertices":[7,8],"edges":[[0,1,5]]}`
Output:
```
graph
0 [label="7"];
1 [label="8"];
0 -- 1 [label="5"];
```

Input: `{"op":"export_dot","directed":true,"vertices":[1,2,3],"edges":[[0,1,4],[1,2,6]]}`
Output:
```
digraph
0 [label="1"];
1 [label="2"];
2 [label="3"];
0 -> 1 [label="4"];
1 -> 2 [label="6"];
```

## Deliverables

- A runnable program that reads one JSON command from stdin and writes the
  specified deterministic text to stdout, implementing all 24 operations above.
- A single entry-point test runner, `rcb_tests/test.sh`, that builds the program
  and executes a directory of JSON cases (`--cases-dir <subdir>`, default
  `test_cases`), writing each case's raw stdout to
  `rcb_tests/stdout/<cases-dir>/<stem>@<NNN>.txt` and reporting a pass/total
  tally.
- The hidden evaluation set under `rcb_tests/test_cases/` and the public mirror
  under `rcb_tests/public_test_cases/`, one `featureN_*.json` file per feature,
  each case shaped as `{"input": ..., "expected_output": ...}`.
