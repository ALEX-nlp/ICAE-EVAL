## Product Requirement Document

# Asynchronous Document Database Client - Promise-Based Database Access Adapter

## Project Goal

Build a document database client library that allows developers to connect to a MongoDB-compatible server, access collections, run database and collection operations, consume cursors asynchronously, and execute bulk writes without manually wrapping callback-oriented driver behavior.

---

## Background & Problem

Without this library/tool, developers are forced to manually create database handles, translate callback-style operations into asynchronous control flow, repeatedly construct command objects, and handle cursor and bulk-write APIs directly. This leads to repetitive boilerplate, inconsistent result handling, and higher risk of mistakes around projections, connection lifecycle, and batched writes.

With this library/tool, developers can use a concise asynchronous interface for common database, collection, cursor, and bulk operations while preserving the externally visible behavior of the underlying database server.

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

### Feature 1: Cursors support sorting, limiting, and projection before materialization

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

A cursor must apply ordering, limits, and field selection before it is materialized into a list.

**Test Cases:** `rcb_tests/public_test_cases/feature10_cursor_materialization.json`

```json
{
    "description": "A cursor must apply ordering, limits, and field selection before it is materialized into a list.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "sort": {
                    "name": 1
                },
                "limit": 1
            },
            "expected_output": "count=1\ndocuments=[{\"name\":\"Charmander\",\"type\":\"fire\"}]\n"
        },
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "projection": {
                    "name": true,
                    "_id": false
                }
            },
            "expected_output": "count=4\ndocuments=[{\"name\":\"Squirtle\"},{\"name\":\"Starmie\"},{\"name\":\"Charmander\"},{\"name\":\"Lapras\"}]\n"
        }
    ]
}
```

---

### Feature 2: Cursors expose iteration state and can be rewound or closed

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

Cursor state operations must report counts and explain availability, advance one document at a time, report no document after exhaustion or close, and allow rewinding to the beginning.

**Test Cases:** `rcb_tests/public_test_cases/feature11_cursor_state_iteration.json`

```json
{
    "description": "Cursor state operations must report counts and explain availability, advance one document at a time, report no document after exhaustion or close, and allow rewinding to the beginning.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "sort": {
                    "name": 1
                },
                "limit": 1
            },
            "expected_output": "count_with_limit=1\nsize_with_limit=1\nexplain_available=yes\nfirst_next=Charmander\nsecond_next=none\nhas_next_before=yes\nhas_next_after=no\nhas_next_after_exhausted=no\nclosed_next=none\ndestroyed_next=none\nrewound_first=Charmander\n"
        }
    ]
}
```

---

### Feature 3: Cursors can be consumed through callbacks and streams

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

A cursor must support callback-style iteration, mapping, readable-stream consumption, and piping, with every seeded document delivered exactly once.

**Test Cases:** `rcb_tests/public_test_cases/feature12_cursor_callbacks_and_streams.json`

```json
{
    "description": "A cursor must support callback-style iteration, mapping, readable-stream consumption, and piping, with every seeded document delivered exactly once.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "sort": {
                    "name": 1
                }
            },
            "expected_output": "for_each_count=4\nmap_names=Charmander,Lapras,Squirtle,Starmie\nstream_count=4\npipe_count=4\n"
        }
    ]
}
```

---

### Feature 4: Collection analysis operations return counts, distinct values, and aggregation output

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

Counting, distinct-value lookup, and aggregation pipelines must produce the expected collection-level analytical results.

**Test Cases:** `rcb_tests/public_test_cases/feature13_collection_counts_distinct_aggregate.json`

```json
{
    "description": "Counting, distinct-value lookup, and aggregation pipelines must produce the expected collection-level analytical results.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "countQuery": {
                    "type": "water"
                },
                "distinctField": "name",
                "distinctQuery": {
                    "type": "water"
                },
                "pipeline": [
                    {
                        "$group": {
                            "_id": "$type"
                        }
                    },
                    {
                        "$project": {
                            "_id": 0,
                            "foo": "$_id"
                        }
                    }
                ]
            },
            "expected_output": "water_count=3\ndistinct_names=Squirtle,Starmie,Lapras\naggregate_types=fire,water\n"
        }
    ]
}
```

---

### Feature 5: Find-and-modify returns either the old or updated document according to input

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

An atomic find-and-modify operation must update the matching document and return either the updated or previous version according to the input flag.

**Test Cases:** `rcb_tests/public_test_cases/feature14_find_and_modify.json`

```json
{
    "description": "An atomic find-and-modify operation must update the matching document and return either the updated or previous version according to the input flag.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "query": {
                    "name": "Squirtle"
                },
                "update": {
                    "$set": {
                        "name": "Squirtle Brawl"
                    }
                },
                "returnUpdated": true
            },
            "expected_output": "returned_name=Squirtle Brawl\n"
        },
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "query": {
                    "name": "Squirtle"
                },
                "update": {
                    "$set": {
                        "name": "Squirtle Brawl"
                    }
                },
                "returnUpdated": false
            },
            "expected_output": "returned_name=Squirtle\n"
        }
    ]
}
```

---

### Feature 6: Updates affect one or many matching documents according to options

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

An update without multi-document mode must affect one match; an update with multi-document mode must affect all matching documents.

**Test Cases:** `rcb_tests/public_test_cases/feature15_update_documents.json`

```json
{
    "description": "An update without multi-document mode must affect one match; an update with multi-document mode must affect all matching documents.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "query": {
                    "type": "water"
                },
                "update": {
                    "$set": {
                        "type": "aqua"
                    }
                },
                "options": {}
            },
            "expected_output": "matched_count=1\nupdated_count=1\nremaining_original_count=2\n"
        },
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "query": {
                    "type": "water"
                },
                "update": {
                    "$set": {
                        "type": "aqua"
                    }
                },
                "options": {
                    "multi": true
                }
            },
            "expected_output": "matched_count=3\nupdated_count=3\nremaining_original_count=0\n"
        }
    ]
}
```

---

### Feature 7: Saving creates new documents and updates existing ones by identifier

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

Saving a document without an identifier must create it with an identifier; saving it again after changing a field must update the existing document.

**Test Cases:** `rcb_tests/public_test_cases/feature16_save_documents.json`

```json
{
    "description": "Saving a document without an identifier must create it with an identifier; saving it again after changing a field must update the existing document.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "newDocument": {
                    "name": "Charizard",
                    "type": "fire"
                },
                "changedType": "flying"
            },
            "expected_output": "created_has_id=yes\ncreated_name=Charizard\nupdated_has_id=yes\nupdated_type=flying\n"
        }
    ]
}
```

---

### Feature 8: Remove operations delete one or all matching documents

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

A removal request must delete either a single matching document or all matching documents based on the input flag and report the number removed.

**Test Cases:** `rcb_tests/public_test_cases/feature17_remove_documents.json`

```json
{
    "description": "A removal request must delete either a single matching document or all matching documents based on the input flag and report the number removed.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "query": {
                    "type": "water"
                },
                "justOne": true
            },
            "expected_output": "removed_count=1\nremaining_count=2\n"
        },
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "query": {
                    "type": "water"
                },
                "justOne": false
            },
            "expected_output": "removed_count=3\nremaining_count=0\n"
        }
    ]
}
```

---

### Feature 9: Collections can be renamed, dropped, inspected, indexed, and capped

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

Collection administration must support renaming, dropping, statistics, index lifecycle operations, reindexing, and capped-collection detection.

**Test Cases:** `rcb_tests/public_test_cases/feature18_collection_administration.json`

```json
{
    "description": "Collection administration must support renaming, dropping, statistics, index lifecycle operations, reindexing, and capped-collection detection.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "renameTo": "b"
            },
            "expected_output": "renamed_collection_count=4\nafter_drop_count=0\nstats_count=4\n"
        },
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "index": {
                    "type": 1
                },
                "cappedCollection": "mycappedcol",
                "cappedOptions": {
                    "capped": true,
                    "size": 1024
                }
            },
            "expected_output": "indexes_after_ensure=2\nindexes_after_drop_all=1\nindexes_after_create=2\nindexes_after_drop_one=1\nindexes_after_reindex=1\ncapped_collection_is_capped=yes\nregular_collection_is_capped=no\n"
        }
    ]
}
```

---

### Feature 10: Bulk write batches execute inserts, replacements, updates, removals, and upserts

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

Bulk operations must split oversized batches, execute replacements, run mixed ordered operations, and treat an empty batch as a successful no-op.

**Test Cases:** `rcb_tests/public_test_cases/feature19_bulk_execution.json`

```json
{
    "description": "Bulk operations must split oversized batches, execute replacements, run mixed ordered operations, and treat an empty batch as a successful no-op.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "insertCount": 1066,
                "document": {
                    "name": "Spearow",
                    "type": "flying"
                }
            },
            "expected_output": "bulk_ok=1\ndocument_count=1066\n"
        },
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water"
                    },
                    {
                        "name": "Starmie",
                        "type": "water"
                    }
                ],
                "replacements": [
                    {
                        "query": {
                            "name": "Squirtle"
                        },
                        "document": {
                            "name": "Charmander",
                            "type": "fire"
                        }
                    },
                    {
                        "query": {
                            "name": "Starmie"
                        },
                        "document": {
                            "type": "fire"
                        }
                    }
                ]
            },
            "expected_output": "bulk_ok=1\ndocuments=[{\"name\":\"Charmander\",\"type\":\"fire\"},{\"name\":\"none\",\"type\":\"fire\"}]\n"
        },
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water"
                    },
                    {
                        "name": "Starmie",
                        "type": "water"
                    },
                    {
                        "name": "Lapras",
                        "type": "water"
                    },
                    {
                        "name": "Charmander",
                        "type": "fire"
                    }
                ]
            },
            "expected_output": "bulk_ok=1\ndocuments=[{\"name\":\"Wartortle\",\"type\":\"water\",\"level\":3,\"hp\":100},{\"name\":\"Starmie\",\"type\":\"water\",\"level\":3,\"hp\":\"none\"},{\"name\":\"Lapras\",\"type\":\"water\",\"level\":3,\"hp\":\"none\"},{\"name\":\"Pidgeotto\",\"type\":\"flying\",\"level\":\"none\",\"hp\":\"none\"},{\"name\":\"Bulbasaur\",\"type\":\"grass\",\"level\":1,\"hp\":\"none\"}]\n"
        },
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water"
                    }
                ]
            },
            "expected_output": "bulk_ok=1\n"
        }
    ]
}
```

---

### Feature 11: Connection strings can omit protocol and host

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

When a database address is supplied in shortened form, the client must connect to the intended local database and return the same query results as the fully qualified address.

**Test Cases:** `rcb_tests/public_test_cases/feature1_connection_shortcuts.json`

```json
{
    "description": "When a database address is supplied in shortened form, the client must connect to the intended local database and return the same query results as the fully qualified address.",
    "cases": [
        {
            "input": {
                "connection": "localhost/test",
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ]
            },
            "expected_output": "document_count=4\nnames=Squirtle,Starmie,Charmander,Lapras\n"
        },
        {
            "input": {
                "connection": "test",
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ]
            },
            "expected_output": "document_count=4\nnames=Squirtle,Starmie,Charmander,Lapras\n"
        }
    ]
}
```

---

### Feature 12: Bulk write plans report queued operation counts

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

A queued bulk plan must be convertible to a representation that reports insert, update, remove, and batch counts before execution.

**Test Cases:** `rcb_tests/public_test_cases/feature20_bulk_representation.json`

```json
{
    "description": "A queued bulk plan must be convertible to a representation that reports insert, update, remove, and batch counts before execution.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "operations": [
                    {
                        "insert": {
                            "item": "abc123",
                            "status": "A",
                            "defaultQty": 500,
                            "points": 5
                        }
                    },
                    {
                        "insert": {
                            "item": "ijk123",
                            "status": "A",
                            "defaultQty": 100,
                            "points": 10
                        }
                    },
                    {
                        "update": {
                            "query": {
                                "item": null
                            },
                            "change": {
                                "$set": {
                                    "item": "TBD"
                                }
                            }
                        }
                    },
                    {
                        "removeOne": {
                            "status": "D"
                        }
                    }
                ],
                "format": "object"
            },
            "expected_output": "nInsertOps=2\nnUpdateOps=1\nnRemoveOps=1\nnBatches=3\n"
        },
        {
            "input": {
                "collection": "a",
                "operations": [
                    {
                        "insert": {
                            "item": "abc123",
                            "status": "A",
                            "defaultQty": 500,
                            "points": 5
                        }
                    },
                    {
                        "insert": {
                            "item": "ijk123",
                            "status": "A",
                            "defaultQty": 100,
                            "points": 10
                        }
                    },
                    {
                        "update": {
                            "query": {
                                "item": null
                            },
                            "change": {
                                "$set": {
                                    "item": "TBD"
                                }
                            }
                        }
                    },
                    {
                        "removeOne": {
                            "status": "D"
                        }
                    }
                ],
                "format": "string"
            },
            "expected_output": "nInsertOps=2\nnUpdateOps=1\nnRemoveOps=1\nnBatches=3\n"
        }
    ]
}
```

---

### Feature 13: Valid collection names are accessible as data collections

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

Accessing a valid collection name through the database facade must produce a usable collection handle, even when the name overlaps with common object property names.

**Test Cases:** `rcb_tests/public_test_cases/feature2_dynamic_collection_access.json`

```json
{
    "description": "Accessing a valid collection name through the database facade must produce a usable collection handle, even when the name overlaps with common object property names.",
    "cases": [
        {
            "input": {
                "collections": [
                    "xyz",
                    "features",
                    "options",
                    "client",
                    "connection",
                    "domain"
                ]
            },
            "expected_output": "collection=xyz\ncount=0\ncollection=features\ncount=0\ncollection=options\ncount=0\ncollection=client\ncount=0\ncollection=connection\ncount=0\ncollection=domain\ncount=0\n"
        }
    ]
}
```

---

### Feature 14: Database catalog operations report collections

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

After creating collections, catalog listing must expose all user collections and their names without reporting internal system collections.

**Test Cases:** `rcb_tests/public_test_cases/feature3_database_catalog.json`

```json
{
    "description": "After creating collections, catalog listing must expose all user collections and their names without reporting internal system collections.",
    "cases": [
        {
            "input": {
                "seedCollection": "a",
                "createCollections": [
                    "test1",
                    "test2"
                ]
            },
            "expected_output": "collection_count=3\nnames=a,test1,test2\n"
        }
    ]
}
```

---

### Feature 15: Database commands and status values are exposed

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

Database-level status commands must return successful command signals, include status fields, and report no previous write error when none has occurred.

**Test Cases:** `rcb_tests/public_test_cases/feature4_database_commands.json`

```json
{
    "description": "Database-level status commands must return successful command signals, include status fields, and report no previous write error when none has occurred.",
    "cases": [
        {
            "input": {
                "seedCollection": "a",
                "scale": 1
            },
            "expected_output": "stats_ok=1\nhas_collections=yes\nhas_indexes=yes\nnamed_command_ok=1\nlast_error=none\nlast_error_object_has_err=no\n"
        }
    ]
}
```

---

### Feature 16: Connection lifecycle events and database deletion are observable

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

The database client must emit a connection signal when a query opens the connection, and dropping a database must remove previously inserted documents from subsequent connections.

**Test Cases:** `rcb_tests/public_test_cases/feature5_database_lifecycle.json`

```json
{
    "description": "The database client must emit a connection signal when a query opens the connection, and dropping a database must remove previously inserted documents from subsequent connections.",
    "cases": [
        {
            "input": {
                "collection": "xyz"
            },
            "expected_output": "connect_event=emitted\nqueried_collection=xyz\nresult_count=0\n"
        },
        {
            "input": {
                "database": "test2",
                "collection": "b",
                "document": {
                    "name": "Squirtle",
                    "type": "water",
                    "level": 10
                }
            },
            "expected_output": "before_drop_count=1\nafter_drop_count=0\n"
        }
    ]
}
```

---

### Feature 17: Database users can be created, rejected as duplicates, and removed

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

Creating a user must succeed once, creating the same user again must be reported as a duplicate-key domain error, and the user must be removable afterward.

**Test Cases:** `rcb_tests/public_test_cases/feature6_user_management.json`

```json
{
    "description": "Creating a user must succeed once, creating the same user again must be reported as a duplicate-key domain error, and the user must be removable afterward.",
    "cases": [
        {
            "input": {
                "user": {
                    "user": "mongoist",
                    "pwd": "topsecret",
                    "customData": {
                        "department": "area51"
                    },
                    "roles": [
                        "readWrite"
                    ]
                }
            },
            "expected_output": "create_ok=1\nduplicate_error=duplicate_key\nduplicate_code=11000\ndrop_ok=1\n"
        }
    ]
}
```

---

### Feature 18: Documents are inserted with generated identifiers

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

Inserting one document or an array of documents must persist every document, preserve caller fields, and generate an identifier for each inserted document.

**Test Cases:** `rcb_tests/public_test_cases/feature7_insert_documents.json`

```json
{
    "description": "Inserting one document or an array of documents must persist every document, preserve caller fields, and generate an identifier for each inserted document.",
    "cases": [
        {
            "input": {
                "collection": "b",
                "documents": {
                    "foo": "bar"
                }
            },
            "expected_output": "inserted_count=1\nhas_generated_id=yes\ndocuments=[{\"foo\":\"bar\"}]\n"
        },
        {
            "input": {
                "collection": "b",
                "documents": [
                    {
                        "foo": "bar"
                    },
                    {
                        "foo": "bar"
                    }
                ],
                "options": {
                    "ordered": true
                }
            },
            "expected_output": "inserted_count=2\nhas_generated_id=yes\ndocuments=[{\"foo\":\"bar\"},{\"foo\":\"bar\"}]\n"
        }
    ]
}
```

---

### Feature 19: Collection queries return matching documents and projections

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

A multi-document query must return all matching documents in stored order, and a projection must include selected fields while omitting unselected fields.

**Test Cases:** `rcb_tests/public_test_cases/feature8_find_many_documents.json`

```json
{
    "description": "A multi-document query must return all matching documents in stored order, and a projection must include selected fields while omitting unselected fields.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "query": {}
            },
            "expected_output": "count=4\ndocuments=[{\"name\":\"Squirtle\",\"type\":\"water\"},{\"name\":\"Starmie\",\"type\":\"water\"},{\"name\":\"Charmander\",\"type\":\"fire\"},{\"name\":\"Lapras\",\"type\":\"water\"}]\n"
        },
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "query": {},
                "projection": {
                    "name": 1
                }
            },
            "expected_output": "count=4\nfirst_has_name=yes\nfirst_has_type=no\n"
        }
    ]
}
```

---

### Feature 20: Single-document queries return the first matching document

**As a developer**, I want to use this database client for this operation, so I can rely on concise asynchronous behavior that matches the database server result.

**Expected Behavior / Usage:**

A single-document query must return the matching document, and projected single-document results must expose selected fields plus the generated identifier while omitting unselected fields.

**Test Cases:** `rcb_tests/public_test_cases/feature9_find_one_document.json`

```json
{
    "description": "A single-document query must return the matching document, and projected single-document results must expose selected fields plus the generated identifier while omitting unselected fields.",
    "cases": [
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "query": {
                    "name": "Squirtle"
                }
            },
            "expected_output": "name=Squirtle\ntype=water\n"
        },
        {
            "input": {
                "collection": "a",
                "seed": [
                    {
                        "name": "Squirtle",
                        "type": "water",
                        "level": 10
                    },
                    {
                        "name": "Starmie",
                        "type": "water",
                        "level": 8
                    },
                    {
                        "name": "Charmander",
                        "type": "fire",
                        "level": 8
                    },
                    {
                        "name": "Lapras",
                        "type": "water",
                        "level": 12
                    }
                ],
                "query": {
                    "name": "Squirtle"
                },
                "projection": {
                    "type": 1
                }
            },
            "expected_output": "has_name=no\ntype=water\nhas_generated_id=yes\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- report 'none' for secondary navigation states like 'second_next' similar to how 'twisted_next' is handled
- use a strict pass validation when the operations array is empty, avoiding any logic branches for empty input
