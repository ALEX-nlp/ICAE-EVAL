## Product Requirement Document

# Vector Similarity Search Library - Approximate and Exhaustive Nearest-Neighbor Operations

## Project Goal

Build a vector similarity search library that allows developers to store high-dimensional numeric vectors, query nearest neighbors, retrieve stored data by labels, and persist search structures without manually implementing high-performance or exhaustive distance search.

---

## Background & Problem

Without this library, developers are forced to scan vector collections manually, implement distance calculations for each metric, manage label-to-vector storage, and rebuild indexes after every process restart. This leads to slow query paths, repetitive persistence code, and error-prone handling of deleted or replaced vectors.

With this library, developers can build a searchable vector collection, query it using common distance interpretations, apply label filters, inspect metadata, persist and reload data structures, and reuse capacity after deletions through a compact public interface.

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

### Feature 1: Nearest-Neighbor Search

**As a developer**, I want to query numeric vectors under supported distance interpretations and optional label predicates, so I can retrieve ranked neighbors that match the search semantics I requested.

**Expected Behavior / Usage:**

*1.1 Metric Distance Ranking — Ranked neighbors and distances for supported metrics*

Given a collection of numeric vectors, a query vector, a distance metric identifier, and a requested neighbor count, the system builds a searchable collection and returns one ranked label row per query along with the corresponding distance row. Squared Euclidean distance ranks by squared coordinate difference, inner-product distance ranks larger dot products as smaller distances using `1 - dot`, and cosine distance ranks by angular similarity using `1 - cosine_similarity`. The stdout contract reports the metric, query count, ranked neighbor labels, and formatted distances.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_metric_distance_ranking.json`

```json
{
    "description": "A small vector collection is queried under each supported distance interpretation, and the nearest labels and distance values are reported in ranked order.",
    "cases": [
        {
            "input": {
                "scenario": "nearest_distances",
                "metric": "l2",
                "vectors": [
                    [
                        1,
                        0,
                        0
                    ],
                    [
                        0,
                        1,
                        0
                    ],
                    [
                        0,
                        0,
                        1
                    ],
                    [
                        1,
                        0,
                        1
                    ],
                    [
                        1,
                        1,
                        1
                    ]
                ],
                "query": [
                    [
                        1,
                        1,
                        1
                    ]
                ],
                "k": 5
            },
            "expected_output": "metric=l2\nquery_count=1\nneighbors=[[4,3,0,1,2]]\ndistances=[[0.000000,1.000000,2.000000,2.000000,2.000000]]\n"
        },
        {
            "input": {
                "scenario": "nearest_distances",
                "metric": "ip",
                "vectors": [
                    [
                        1,
                        0,
                        0
                    ],
                    [
                        0,
                        1,
                        0
                    ],
                    [
                        0,
                        0,
                        1
                    ],
                    [
                        1,
                        0,
                        1
                    ],
                    [
                        1,
                        1,
                        1
                    ]
                ],
                "query": [
                    [
                        1,
                        1,
                        1
                    ]
                ],
                "k": 5
            },
            "expected_output": "metric=ip\nquery_count=1\nneighbors=[[4,3,0,1,2]]\ndistances=[[[a specific negative inner product value — ask the PM for the exact float],-1.000000,0.000000,0.000000,0.000000]]\n"
        },
        {
            "input": {
                "scenario": "nearest_distances",
                "metric": "cosine",
                "vectors": [
                    [
                        1,
                        0,
                        0
                    ],
                    [
                        0,
                        1,
                        0
                    ],
                    [
                        0,
                        0,
                        1
                    ],
                    [
                        1,
                        0,
                        1
                    ],
                    [
                        1,
                        1,
                        1
                    ]
                ],
                "query": [
                    [
                        1,
                        1,
                        1
                    ]
                ],
                "k": 5
            },
            "expected_output": "metric=cosine\nquery_count=1\nneighbors=[[4,3,0,1,2]]\ndistances=[[0.000000,0.183503,0.422650,0.422650,0.422650]]\n"
        }
    ]
}
```

*1.2 Filtered Search — Predicate-restricted nearest-neighbor search*

Given a vector collection and a label predicate, both approximate indexed search and exhaustive search must return only labels accepted by the predicate. The stdout contract reports each engine's selected labels, the fraction of queries whose own label remains selectable, and the count of labels that violated the predicate.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_filtered_search.json`

```json
{
    "description": "A nearest-neighbor query is executed with a predicate that permits only even-numbered labels, and both approximate and exhaustive search results must honor the predicate.",
    "cases": [
        {
            "input": {
                "scenario": "filtered_even_search",
                "metric": "l2",
                "vectors": [
                    [
                        0
                    ],
                    [
                        10
                    ],
                    [
                        20
                    ],
                    [
                        30
                    ],
                    [
                        40
                    ],
                    [
                        50
                    ],
                    [
                        60
                    ],
                    [
                        70
                    ],
                    [
                        80
                    ],
                    [
                        90
                    ]
                ]
            },
            "expected_output": "metric=l2\nquery_count=10\napproximate_labels=[the specific sorted list of even indices found in the test vectors — ask the dev lead for the array]\nbruteforce_labels=[the specific sorted list of even indices found in the test vectors — ask the dev lead for the array]\napproximate_exact_self_fraction=0.500000\nbruteforce_exact_self_fraction=0.500000\napproximate_odd_label_count=0\nbruteforce_odd_label_count=0\n"
        }
    ]
}
```

---

### Feature 2: Stored Vector Retrieval

**As a developer**, I want to retrieve vectors by external labels after insertion and receive normalized errors for invalid retrieval requests, so I can treat the vector store as a reliable label-addressed data source.

**Expected Behavior / Usage:**

*2.1 Retrieve Stored Vectors — Label-addressed data access*

Given stored vectors with external labels and a requested label sequence, the system returns the original vector values in the same order as the requested labels. The caller may request an array-shaped rendering or a list-shaped rendering; stdout reports the selected rendering format, row count, and vector rows.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_retrieve_stored_vectors.json`

```json
{
    "description": "Stored vectors are retrieved by their external labels, preserving requested order and supporting array-shaped and list-shaped output renderings.",
    "cases": [
        {
            "input": {
                "scenario": "retrieve_vectors",
                "metric": "l2",
                "vectors": [
                    [
                        0.1,
                        0.2
                    ],
                    [
                        0.3,
                        0.4
                    ],
                    [
                        0.5,
                        0.6
                    ]
                ],
                "labels": [
                    101,
                    102,
                    103
                ],
                "requested_labels": [
                    103,
                    101
                ],
                "format": "array"
            },
            "expected_output": "format=array\nrow_count=2\nitems=[[0.500000,0.600000];[0.[the default construction width used when connectivity is not specified — check default config or ask PM]000,0.200000]]\n"
        },
        {
            "input": {
                "scenario": "retrieve_vectors",
                "metric": "l2",
                "vectors": [
                    [
                        0.1,
                        0.2
                    ],
                    [
                        0.3,
                        0.4
                    ],
                    [
                        0.5,
                        0.6
                    ]
                ],
                "labels": [
                    101,
                    102,
                    103
                ],
                "requested_labels": [
                    102,
                    103
                ],
                "format": "list"
            },
            "expected_output": "format=list\nrow_count=2\nitems=[[0.300000,0.400000];[0.500000,0.600000]]\n"
        }
    ]
}
```

*2.2 Retrieval Error Conditions — Normalized retrieval failures*

When retrieval is attempted before any vectors have been inserted, stdout must report `error=items_unavailable` with the empty-store stage. When a single scalar label is supplied where a collection of labels is required, stdout must report `error=invalid_label_collection` and the raw label value. These errors are language-neutral and must not expose host-runtime exception names or runtime-generated messages.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_retrieval_error_conditions.json`

```json
{
    "description": "Retrieval requests that cannot identify a collection of stored labels are reported as normalized domain errors without exposing host-runtime exception names.",
    "cases": [
        {
            "input": {
                "scenario": "retrieve_before_add",
                "metric": "l2",
                "dim": 2,
                "capacity": 3,
                "requested_labels": [
                    1,
                    2
                ]
            },
            "expected_output": "error=items_unavailable\nstage=empty_store\n"
        },
        {
            "input": {
                "scenario": "retrieve_scalar_label_error",
                "metric": "l2",
                "vectors": [
                    [
                        0.1,
                        0.2
                    ],
                    [
                        0.3,
                        0.4
                    ]
                ],
                "labels": [
                    5,
                    6
                ],
                "requested_label": 5
            },
            "expected_output": "error=invalid_label_collection\nlabel=5\n"
        }
    ]
}
```

---

### Feature 3: Index Metadata

**As a developer**, I want to inspect configured index parameters and live element counts, so I can verify capacity, dimensionality, and construction settings after loading data.

**Expected Behavior / Usage:**

Given a configured vector index and an inserted vector batch, the system reports the active metric, dimensionality, connectivity setting, construction search width, maximum capacity, and current count. These values must reflect the user-visible configuration and inserted data rather than internal storage details.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_index_metadata.json`

```json
{
    "description": "After vectors are inserted, the index reports its configured metric, dimensionality, graph construction parameters, capacity, and current element count.",
    "cases": [
        {
            "input": {
                "scenario": "metadata_after_add",
                "metric": "l2",
                "capacity": 6,
                "vectors": [
                    [
                        0,
                        0
                    ],
                    [
                        1,
                        1
                    ],
                    [
                        2,
                        2
                    ]
                ],
                "connectivity": 16
            },
            "expected_output": "metric=l2\ndim=2\nconnectivity=16\nconstruction_width=[the default construction width used when connectivity is not specified — check default config or ask PM]\ncapacity=6\ncount=3\n"
        }
    ]
}
```

---

### Feature 4: Persistence and Reloading

**As a developer**, I want saved vector search structures to reload with the same observable query behavior and support continued use, so I can persist work across processes.

**Expected Behavior / Usage:**

*4.1 Save, Load, and Append — Continue using a saved graph index*

Given an index saved after an initial vector batch, loading the saved file must preserve the stored vectors and allow a later batch to be inserted. A nearest-neighbor query over all inserted vectors must return every vector as its own nearest neighbor. Stdout reports the saved count, final loaded count, self-recall, and returned labels.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_save_load_and_append.json`

```json
{
    "description": "An index saved after an initial batch can be loaded again, extended with another batch, and still return every stored vector as its own nearest neighbor.",
    "cases": [
        {
            "input": {
                "scenario": "save_load_append",
                "metric": "l2",
                "vectors": [
                    [
                        0,
                        0
                    ],
                    [
                        1,
                        0
                    ],
                    [
                        0,
                        1
                    ],
                    [
                        1,
                        1
                    ],
                    [
                        2,
                        2
                    ],
                    [
                        3,
                        3
                    ]
                ],
                "first_batch_size": 3
            },
            "expected_output": "saved_count=3\nloaded_then_count=6\nself_recall=1.000000\nlabels=[0,1,2,3,4,5]\n"
        }
    ]
}
```

*4.2 Exhaustive Search Save and Load — Preserve exact-search results*

Given an exhaustive vector store, saving and loading it must preserve the labels and distance values returned for the same query. Stdout reports labels and distances before and after loading, plus a numeric same-labels signal.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_bruteforce_save_load.json`

```json
{
    "description": "An exhaustive vector store saved to disk and loaded again returns the same nearest labels and distances for the same query.",
    "cases": [
        {
            "input": {
                "scenario": "bruteforce_save_load",
                "metric": "l2",
                "vectors": [
                    [
                        0,
                        0
                    ],
                    [
                        1,
                        0
                    ],
                    [
                        0,
                        2
                    ],
                    [
                        2,
                        2
                    ]
                ],
                "query": [
                    [
                        1,
                        1
                    ]
                ],
                "k": 3
            },
            "expected_output": "metric=l2\nlabels_before=[[1,0,2]]\nlabels_after=[[1,0,2]]\ndistances_before=[[1.000000,2.000000,2.000000]]\ndistances_after=[[1.000000,2.000000,2.000000]]\nsame_labels=1\n"
        }
    ]
}
```

---

### Feature 5: Deletion, Restoration, and Replacement

**As a developer**, I want deleted labels to disappear from search results, restored labels to become searchable again, and replacement-enabled indexes to reuse deleted capacity, so I can maintain a fixed-capacity vector collection over time.

**Expected Behavior / Usage:**

*5.1 Delete and Restore Labels — Search visibility follows label state*

Given stored vectors and a set of labels to delete, nearest-neighbor queries for the deleted vectors must not return those deleted labels while they remain deleted. After the same labels are restored, the vectors must again return their own labels as nearest neighbors. Stdout reports the deleted labels, nearest labels while deleted, overlap count with deleted labels, restored nearest labels, and restored recall.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_delete_and_restore_labels.json`

```json
{
    "description": "Deleted labels are excluded from nearest-neighbor results, and restoring those labels makes their vectors searchable again.",
    "cases": [
        {
            "input": {
                "scenario": "delete_restore",
                "metric": "l2",
                "vectors": [
                    [
                        0,
                        0
                    ],
                    [
                        10,
                        0
                    ],
                    [
                        20,
                        0
                    ],
                    [
                        30,
                        0
                    ],
                    [
                        40,
                        0
                    ],
                    [
                        50,
                        0
                    ]
                ],
                "delete_labels": [
                    1,
                    3
                ]
            },
            "expected_output": "deleted_labels=[1,3]\nafter_delete_neighbors=[0,4]\nafter_delete_overlap=0\nrestored_neighbors=[1,3]\nrestored_recall=1.000000\n"
        }
    ]
}
```

*5.2 Replace Deleted Slots — Reuse fixed capacity for new labels*

Given a full index configured to allow replacement, deleting labels creates reusable slots. Adding a replacement batch with new labels must occupy those deleted slots without increasing capacity, and the replacement vectors must be retrievable and searchable under their new labels. Stdout reports capacity, count, replacement labels, replacement vector values, nearest labels for replacement queries, and replacement recall.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_replace_deleted_slots.json`

```json
{
    "description": "When replacement is enabled at fixed capacity, newly supplied vectors can occupy deleted slots and are retrievable by their new labels.",
    "cases": [
        {
            "input": {
                "scenario": "replace_deleted",
                "metric": "l2",
                "initial_vectors": [
                    [
                        0,
                        0
                    ],
                    [
                        10,
                        0
                    ],
                    [
                        20,
                        0
                    ],
                    [
                        [the default construction width used when connectivity is not specified — check default config or ask PM],
                        0
                    ],
                    [
                        110,
                        0
                    ],
                    [
                        120,
                        0
                    ]
                ],
                "initial_labels": [
                    0,
                    1,
                    2,
                    3,
                    4,
                    5
                ],
                "delete_labels": [
                    3,
                    4,
                    5
                ],
                "replacement_vectors": [
                    [
                        30,
                        0
                    ],
                    [
                        40,
                        0
                    ],
                    [
                        50,
                        0
                    ]
                ],
                "replacement_labels": [
                    6,
                    7,
                    8
                ]
            },
            "expected_output": "capacity=6\ncount=6\nreplacement_labels=[6,7,8]\nreplacement_items=[[30.000000,0.000000];[40.000000,0.000000];[50.000000,0.000000]]\nreplacement_neighbors=[6,7,8]\nreplacement_recall=1.000000\n"
        }
    ]
}
```

*5.3 Replacement After Reload — Reusable deletion state survives serialization*

Given a replacement-enabled index with deleted replacement labels, saving and loading the index must preserve enough deletion state to accept a second replacement batch. Object serialization must also preserve the query behavior for that second replacement batch. Stdout reports loaded count, second replacement labels, loaded nearest labels and recall, and object-serialized nearest labels and recall.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_replace_deleted_after_reload.json`

```json
{
    "description": "Deleted replacement slots remain reusable after file serialization and after object serialization, and the reloaded index finds the second replacement batch by its labels.",
    "cases": [
        {
            "input": {
                "scenario": "replace_deleted_after_reload",
                "metric": "l2",
                "initial_vectors": [
                    [
                        0,
                        0
                    ],
                    [
                        10,
                        0
                    ],
                    [
                        20,
                        0
                    ],
                    [
                        [the default construction width used when connectivity is not specified — check default config or ask PM],
                        0
                    ],
                    [
                        110,
                        0
                    ],
                    [
                        120,
                        0
                    ]
                ],
                "initial_labels": [
                    0,
                    1,
                    2,
                    3,
                    4,
                    5
                ],
                "delete_labels": [
                    3,
                    4,
                    5
                ],
                "first_replacement_vectors": [
                    [
                        30,
                        0
                    ],
                    [
                        40,
                        0
                    ],
                    [
                        50,
                        0
                    ]
                ],
                "first_replacement_labels": [
                    6,
                    7,
                    8
                ],
                "second_replacement_vectors": [
                    [
                        60,
                        0
                    ],
                    [
                        70,
                        0
                    ],
                    [
                        80,
                        0
                    ]
                ],
                "second_replacement_labels": [
                    9,
                    10,
                    11
                ]
            },
            "expected_output": "loaded_count=6\nsecond_replacement_labels=[9,10,11]\nloaded_neighbors=[9,10,11]\nloaded_recall=1.000000\npickled_neighbors=[9,10,11]\npickled_recall=1.000000\n"
        }
    ]
}
```

---

### Feature 6: Capacity Resizing

**As a developer**, I want to increase an index's capacity after inserting an initial batch, so I can append more vectors without rebuilding from scratch.

**Expected Behavior / Usage:**

Given an index initialized with a smaller capacity than the full vector collection, resizing upward must update the reported capacity, allow the remaining vectors to be inserted, expose all labels, and preserve self-neighbor search for every vector. Stdout reports capacity before and after resizing, current count, sorted labels, and self-recall.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_resize_capacity.json`

```json
{
    "description": "An index initialized with a smaller capacity can be resized upward, accept the remaining vectors, and report all labels while preserving self-neighbor search.",
    "cases": [
        {
            "input": {
                "scenario": "resize_capacity",
                "metric": "l2",
                "first_capacity": 3,
                "vectors": [
                    [
                        0,
                        0
                    ],
                    [
                        1,
                        0
                    ],
                    [
                        2,
                        0
                    ],
                    [
                        3,
                        0
                    ],
                    [
                        4,
                        0
                    ],
                    [
                        5,
                        0
                    ]
                ]
            },
            "expected_output": "capacity_before=3\ncapacity_after=6\ncount=6\nids=[0,1,2,3,4,5]\nself_recall=1.000000\n"
        }
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
- follow the standard key=value delimiter used throughout the logging module
- use the exact error formatting pattern defined in the domain error handler class
