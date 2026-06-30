## Product Requirement Document

# Ordered List Positioning Engine - A Reusable Mixin for Maintaining Ordered Records

## Project Goal

Build a library that turns an ordinary persisted record type into an ordered list, where every record carries an integer position and the collection as a whole is kept contiguously numbered automatically. Developers should be able to append, prepend, insert, move, remove, and re-scope records and trust that the surrounding positions are always renumbered correctly, without writing any of the bookkeeping by hand.

---

## Background & Problem

Without such a library, developers who need an explicit, user-visible ordering on a set of records are forced to manage a position integer manually: when a record is inserted in the middle, every record after it must be bumped down by one; when a record is removed or deleted, the gap it leaves must be closed; when a record moves from one position to another, all the records in between must be shifted in the right direction. Each of these operations is easy to get subtly wrong (off-by-one shifts, duplicated positions, gaps that never close), and the bugs multiply once the same table holds several independent lists distinguished by some grouping key.

With this library, a record type is declared to be list-managed once, and from then on creation, insertion at an explicit slot, relative moves (up/down/to-top/to-bottom), absolute relocation, removal, deletion, and changing the grouping key all keep the affected list(s) contiguous and duplicate-free automatically. The behavior is tunable: where numbering starts, whether new records go to the top or the bottom or stay out of the list entirely, whether one or several keys partition the table into independent sub-lists, whether reordering touches modified-timestamps, and whether intermediate shifts happen one row at a time so a unique index is never transiently violated.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility system (configuration of list behavior, position computation/renumbering, scope partitioning, persistence hooks, and the execution adapter that drives it). It MUST NOT be a single "god file"; use a clear, multi-file directory tree reflecting a production-grade repository. Do not over-engineer, but avoid monolithic files.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core list-positioning logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls into the core domain.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units (SRP). The core engine should be open for extension but closed for modification (OCP). Keep interfaces small and cohesive (ISP), and have high-level modules depend on abstractions rather than on low-level persistence/I/O details (DIP).

4. **Robustness & Interface Design:** The public interface of the core system must be elegant and idiomatic to the target language, hiding internal complexity. The system must handle edge cases gracefully and model errors properly rather than relying on generic faults.

---

## Conventions used by the test contract

Each case provides a `config` object (how the list behaves), an ordered list of `operations` to perform, and a list of `queries` that produce the output. The execution adapter applies operations in order against a fresh, empty store, then evaluates each query and prints one line per query (in order) to stdout.

- `config` knobs: `column` (the position field name); `scope` (a grouping key, or list of keys, that partitions records into independent sub-lists); `add_new_at` (`"bottom"` default, `"top"`, or `null` meaning new records are not auto-placed); `top_of_list` (the integer the first slot uses, default `1`); `sequential_updates` (force stepwise shifting on/off); `touch_on_update` (whether reordering refreshes modified-timestamps; default on); `unique`/`positive` (the position field is backed by a unique index / constrained to be greater than zero).
- `operations` vocabulary: `create` (new record with optional `attrs`), `insert_at` (relocate to an absolute target position), `set_position` (assign a position value directly and persist), `move_up`/`move_down` (one step toward front/back), `move_to_top`/`move_to_bottom`, `remove` (take out of the list), `delete` (destroy the record), `update` (change attributes, possibly the scope key and/or position), `suspend_maintenance` (run a nested block with automatic renumbering switched off), `at_time` (run a nested block as though "now" were the named instant `base` or `later`).
- `queries` vocabulary and output lines: `order_ids` → `ids=[...]` (record identifiers in the requested order, where identifiers are assigned 1,2,3,... in creation order); `position_values` → `positions=[...]`; `position_of` → `position=<n>` (or `position=nil`); `item_status` → `position=<n> first=<bool> last=<bool> in_list=<bool>`; `predecessor`/`successor` → `predecessor=<id>`/`successor=<id>` (or `nil`); `predecessors`/`successors` → `predecessors=[...]`/`successors=[...]` (nearest first, optional `limit`); `timestamp_buckets` → `timestamps=[...]` (each remaining record's modified-timestamp bucketed as `base` or `later`); `stepwise_shuffle` → `stepwise_shuffle=<bool>`; `insert_at_outcome`/`suspend_argument_outcome` → a normalized `error=<category>` line. An empty value is rendered as `nil`; missing record positions are `nil`. A `where` filter and `order` field on a query restrict and sort the records it reports.

Errors are normalized to neutral, language-independent `error=<category>` lines; no host-language exception names or runtime artifacts appear in stdout.

---

## Core Features

### Feature 1: Append new records to the end of the list

**As a developer**, I want each newly created record to land at the end of its list with the next sequential position, so I can build an ordered collection just by creating records.

**Expected Behavior / Usage:**

By default a created record is appended and receives the next position, with numbering starting at one. Creating several records into the same (initially empty) list yields strictly increasing positions in creation order. A status query for any record reports its position, whether it is the first element (nothing precedes it), whether it is the last element (nothing follows it), and whether it currently participates in the ordering.

**Test Cases:** `rcb_tests/public_test_cases/feature1_add_at_bottom.json`

```json
{
    "description": "By default a new record is appended to the end of its list and receives the next sequential position, with the list numbered starting at one. Creating several records into the same empty list yields strictly increasing positions in creation order. For any record the status reports its position, whether it is the first element of the list, whether it is the last element, and whether it currently participates in the ordering. A record is 'first' when no element precedes it and 'last' when none follows it.",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 20}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 20}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 20}}
                ],
                "queries": [
                    {"q": "item_status", "ref": "a"},
                    {"q": "item_status", "ref": "b"},
                    {"q": "item_status", "ref": "c"},
                    {"q": "order_ids", "where": {"parent_id": 20}, "order": "position"}
                ]
            },
            "expected_output": "position=1 first=true last=false in_list=true\nposition=2 first=false last=false in_list=true\nposition=3 first=false last=true in_list=true\nids=[1, 2, 3]"
        }
    ]
}
```

---

### Feature 2: Prepend new records to the front of the list

**As a developer**, I want to configure a list so new records go to the top and push the rest down, so the most recently added record reads first.

**Expected Behavior / Usage:**

When the list is configured to add new records at the top, each new record (with no explicit position) takes the top slot and shifts the existing elements one place toward the back, so reading the list in position order shows the newest record first. If an explicit position is supplied at creation time, that value is honored instead of the automatic top placement.

**Test Cases:** `rcb_tests/public_test_cases/feature2_add_at_top.json`

```json
{
    "description": "A list can be configured so that new records are prepended to the front instead of appended to the back. Under this configuration, each newly created record (when no explicit position is supplied) takes the top position and pushes the existing elements one place toward the back, so the most recently created record appears first when the list is read in position order. If, however, an explicit position value is supplied at creation time, that supplied value is honored rather than the automatic top placement.",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id", "add_new_at": "top"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 20}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 20}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 20}}
                ],
                "queries": [
                    {"q": "order_ids", "where": {"parent_id": 20}, "order": "position"},
                    {"q": "item_status", "ref": "c"}
                ]
            },
            "expected_output": "[example array of IDs shifting down]\nposition=1 first=true last=false in_list=true"
        }
    ]
}
```

---

### Feature 3: Create records without auto-placement

**As a developer**, I want to configure a list so new records are not automatically added to the ordering, so I can decide later when (or whether) a record joins the list.

**Expected Behavior / Usage:**

When auto-placement is disabled, a created record has no position assigned (its position is empty) and does not participate in the list, so it reports as not being in the list. Updating an unrelated attribute on such a record does not draw it into the ordering: its position stays empty and it remains outside the list.

**Test Cases:** `rcb_tests/public_test_cases/feature3_no_auto_add.json`

```json
{
    "description": "A list can be configured so that newly created records are NOT automatically placed into the ordering. Under this configuration a created record has no position assigned (its position is empty) and it does not participate in the list, so it reports as not being in the list. A subsequent update of an unrelated attribute on such a record does not draw it into the ordering either: its position remains empty and it remains outside the list.",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id", "add_new_at": null},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 20}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 20}}
                ],
                "queries": [
                    {"q": "item_status", "ref": "a"},
                    {"q": "item_status", "ref": "b"}
                ]
            },
            "expected_output": "position=nil first=false last=false in_list=false\nposition=nil first=false last=false in_list=false"
        }
    ]
}
```

---

### Feature 4: Configurable starting index (zero-based lists)

**As a developer**, I want to choose the integer that the top of the list uses, so I can make a list behave like a zero-indexed array when that fits my domain.

**Expected Behavior / Usage:**

The top-of-list integer is configurable. When set to zero, new records appended to an empty list start at position zero and increase by one, and the first element reports position zero. Repositioning by an absolute target uses the same zero-based scale.

**Test Cases:** `rcb_tests/public_test_cases/feature4_zero_based_indexing.json`

```json
{
    "description": "The integer used for the top of the list is configurable; when it is set to zero, the list behaves like a zero-indexed array. New records appended to an empty list then start at position zero and increase by one, and the first element of the list reports position zero. Repositioning an element by an absolute target position uses the same zero-based scale.",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id", "top_of_list": 0},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 20}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 20}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 20}}
                ],
                "queries": [
                    {"q": "item_status", "ref": "a"},
                    {"q": "item_status", "ref": "c"},
                    {"q": "order_ids", "where": {"parent_id": 20}, "order": "position"},
                    {"q": "position_values", "where": {"parent_id": 20}, "order": "position"}
                ]
            },
            "expected_output": "position=0 first=true last=false in_list=true\nposition=2 first=false last=true in_list=true\nids=[1, 2, 3]\npositions=[0, 1, 2]"
        }
    ]
}
```

---

### Feature 5: Create at an explicit position

**As a developer**, I want to create a record at a specific slot, so the surrounding records make room automatically.

**Expected Behavior / Usage:**

When a record is created with an explicit position rather than defaulting to the end, it is inserted at exactly that position, and every existing element at or below that slot shifts one place toward the back to make room. The list stays contiguously numbered, and reading it in position order shows the new record occupying the requested slot.

**Test Cases:** `rcb_tests/public_test_cases/feature5_create_at_position.json`

```json
{
    "description": "When a record is created with an explicit position value rather than letting it default to the end, the record is inserted at that exact position and every existing element at or below that position is shifted one place toward the back to make room. The list remains contiguously numbered after the insertion, and reading it in position order shows the new record occupying the requested slot.",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 5, "position": 1}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 5, "position": 2}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 5, "position": 3}},
                    {"op": "create", "ref": "d", "attrs": {"parent_id": 5, "position": 4}},
                    {"op": "create", "ref": "e", "attrs": {"parent_id": 5, "position": 1}}
                ],
                "queries": [
                    {"q": "order_ids", "where": {"parent_id": 5}, "order": "position"},
                    {"q": "position_values", "where": {"parent_id": 5}, "order": "position"}
                ]
            },
            "expected_output": "ids=[5, 1, 2, 3, 4]\npositions=[1, 2, 3, 4, 5]"
        },
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 5, "position": 1}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 5, "position": 2}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 5, "position": 3}},
                    {"op": "create", "ref": "d", "attrs": {"parent_id": 5, "position": 4}},
                    {"op": "create", "ref": "e", "attrs": {"parent_id": 5, "position": 3}}
                ],
                "queries": [
                    {"q": "order_ids", "where": {"parent_id": 5}, "order": "position"},
                    {"q": "position_values", "where": {"parent_id": 5}, "order": "position"}
                ]
            },
            "expected_output": "ids=[1, 2, 5, 3, 4]\npositions=[1, 2, 3, 4, 5]"
        }
    ]
}
```

---

### Feature 6: Neighbor and membership queries

**As a developer**, I want to ask for a record's immediate neighbor on either side and whether it is currently in the list, so I can navigate and inspect the ordering.

**Expected Behavior / Usage:**

For any element you can request its immediate predecessor (one place ahead) and immediate successor (one place behind); the head has no predecessor and the tail has no successor. You can also ask whether an element is currently in the list and what its position is; an element taken out of the list reports no position and is no longer first, last, or in the list.

**Test Cases:** `rcb_tests/public_test_cases/feature6_relationship_queries.json`

```json
{
    "description": "For any element in the list you can ask for its immediate predecessor (the element one place ahead of it) and its immediate successor (the element one place behind it). The head of the list has no predecessor and the tail has no successor. You can also ask whether an element is currently in the list and what its current position is; an element that has been taken out of the list reports no position and is no longer first, last, or in the list.",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 5, "position": 1}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 5, "position": 2}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 5, "position": 3}},
                    {"op": "create", "ref": "d", "attrs": {"parent_id": 5, "position": 4}}
                ],
                "queries": [
                    {"q": "successor", "ref": "a"},
                    {"q": "predecessor", "ref": "a"},
                    {"q": "predecessor", "ref": "d"},
                    {"q": "successor", "ref": "d"}
                ]
            },
            "expected_output": "successor=2\npredecessor=nil\npredecessor=3\nsuccessor=nil"
        }
    ]
}
```

---

### Feature 7: Grouped neighbor queries

**As a developer**, I want the ordered group of all records that follow or precede a given record (optionally capped), so I can work with ranges of neighbors.

**Expected Behavior / Usage:**

You can request all elements that follow a given element (its successors, nearest first) or all that precede it (its predecessors, nearest first). An optional limit caps how many are returned. The head has no predecessors and the tail no successors. Predecessors come back in order of increasing distance toward the front; successors in order of increasing distance toward the back.

**Test Cases:** `rcb_tests/public_test_cases/feature7_neighbor_groups.json`

```json
{
    "description": "Beyond a single neighbor, you can request the ordered group of all elements that follow a given element (its successors, nearest first) or all elements that precede it (its predecessors, nearest first). An optional limit caps how many are returned. The head of the list has no predecessors and the tail has no successors. Predecessors are returned in order of increasing distance going toward the front, and successors in order of increasing distance going toward the back.",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 5, "position": 1}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 5, "position": 2}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 5, "position": 3}},
                    {"op": "create", "ref": "d", "attrs": {"parent_id": 5, "position": 4}}
                ],
                "queries": [
                    {"q": "successors", "ref": "a"},
                    {"q": "successors", "ref": "c"},
                    {"q": "successors", "ref": "a", "limit": 2},
                    {"q": "successors", "ref": "d"},
                    {"q": "predecessors", "ref": "c"},
                    {"q": "predecessors", "ref": "b"},
                    {"q": "predecessors", "ref": "d", "limit": 2},
                    {"q": "predecessors", "ref": "a"}
                ]
            },
            "expected_output": "successors=[2, 3, 4]\nsuccessors=[4]\nsuccessors=[2, 3]\nsuccessors=[]\npredecessors=[2, 1]\npredecessors=[1]\npredecessors=[3, 2]\npredecessors=[]"
        }
    ]
}
```

---

### Feature 8: Relative moves

**As a developer**, I want to nudge a record one step in either direction or send it to an end, so I can reorder without computing positions myself.

**Expected Behavior / Usage:**

Moving an element one step toward the back swaps it with its immediate successor; one step toward the front swaps it with its immediate predecessor. Moving it to the very front or very back relocates it there and shifts the intervening elements accordingly. The remaining elements always close ranks so numbering stays contiguous.

**Test Cases:** `rcb_tests/public_test_cases/feature8_relative_moves.json`

```json
{
    "description": "An element can be moved relative to its neighbors or to the ends of the list while the remaining elements close ranks to keep the numbering contiguous. Moving an element one step toward the back swaps it with its immediate successor; moving it one step toward the front swaps it with its immediate predecessor. Moving an element to the very front or the very back relocates it there and shifts the intervening elements accordingly. Each case sets up a four-element list numbered one through four (identifiers also one through four in that order) and performs a single move, then reads the resulting order of identifiers.",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 5, "position": 1}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 5, "position": 2}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 5, "position": 3}},
                    {"op": "create", "ref": "d", "attrs": {"parent_id": 5, "position": 4}},
                    {"op": "move_down", "ref": "b"}
                ],
                "queries": [
                    {"q": "order_ids", "where": {"parent_id": 5}, "order": "position"}
                ]
            },
            "expected_output": "ids=[1, 3, 2, 4]"
        },
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 5, "position": 1}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 5, "position": 2}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 5, "position": 3}},
                    {"op": "create", "ref": "d", "attrs": {"parent_id": 5, "position": 4}},
                    {"op": "move_to_bottom", "ref": "a"}
                ],
                "queries": [
                    {"q": "order_ids", "where": {"parent_id": 5}, "order": "position"}
                ]
            },
            "expected_output": "ids=[2, 3, 4, 1]"
        }
    ]
}
```

---

### Feature 9: Relocate to an absolute position

**As a developer**, I want to move an existing record to an absolute target slot, so the records in between shift to absorb the move.

**Expected Behavior / Usage:**

Relocating an element to an absolute target shifts the intervening elements between its old and new positions by one place, and the list stays contiguously numbered. Moving toward the back shifts the in-between elements one place toward the front; moving toward the front shifts them one place toward the back.

**Test Cases:** `rcb_tests/public_test_cases/feature9_insert_at.json`

```json
{
    "description": "An element already in the list can be relocated to an absolute target position. The intervening elements between the element's old and new position shift by one place to absorb the move, and the list stays contiguously numbered. Moving toward the back shifts the elements in between one place toward the front; moving toward the front shifts them one place toward the back. Each case starts from a four-element list numbered one through four (identifiers one through four in that order) and relocates one element, then reads the resulting identifier order and position values.",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 5, "position": 1}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 5, "position": 2}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 5, "position": 3}},
                    {"op": "create", "ref": "d", "attrs": {"parent_id": 5, "position": 4}},
                    {"op": "insert_at", "ref": "d", "position": 2}
                ],
                "queries": [
                    {"q": "order_ids", "where": {"parent_id": 5}, "order": "position"},
                    {"q": "position_values", "where": {"parent_id": 5}, "order": "position"}
                ]
            },
            "expected_output": "ids=[1, 4, 2, 3]\npositions=[1, 2, 3, 4]"
        }
    ]
}
```

---

### Feature 10: Assign a position directly

**As a developer**, I want to set a record's position value directly and have the rest reorder, so an absolute assignment behaves like a relocation.

**Expected Behavior / Usage:**

Setting a record's position value directly (and persisting it) relocates the element and reorders the others so the list stays contiguous with no duplicates. The effect matches relocating to that target: elements between the old and new slot shift by one to absorb the change.

**Test Cases:** `rcb_tests/public_test_cases/feature10_set_position.json`

```json
{
    "description": "Assigning an element a new absolute position by setting its position value directly (and persisting it) relocates the element and reorders the others so the list stays contiguous with no duplicates. The effect matches relocating the element to that target position: elements between the old and new slot shift by one to absorb the change. Each case uses an unscoped (single, global) list of four elements numbered one through four (identifiers one through four) and sets one element's position, then reads the resulting identifier order.",
    "cases": [
        {
            "input": {
                "config": {"column": "position"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"position": 1}},
                    {"op": "create", "ref": "b", "attrs": {"position": 2}},
                    {"op": "create", "ref": "c", "attrs": {"position": 3}},
                    {"op": "create", "ref": "d", "attrs": {"position": 4}},
                    {"op": "set_position", "ref": "b", "position": 4}
                ],
                "queries": [
                    {"q": "order_ids", "order": "position"}
                ]
            },
            "expected_output": "ids=[1, 3, 4, 2]"
        }
    ]
}
```

---

### Feature 11: Remove from the list

**As a developer**, I want to take a record out of the ordering without deleting it, so the gap closes and the record reports as no longer participating.

**Expected Behavior / Usage:**

Taking an element out clears its position (it becomes empty) and shifts every element behind it one place toward the front so the remaining list is contiguous; the removed element reports as no longer in the list. Removing an element and then deleting that same record does not shift the trailing elements a second time.

**Test Cases:** `rcb_tests/public_test_cases/feature11_remove_from_list.json`

```json
{
    "description": "Taking an element out of the ordering clears its position (it becomes empty) and shifts every element that was behind it one place toward the front so the remaining list is contiguous; the removed element reports as no longer in the list. Removing an element and then deleting that same record does not shift the trailing elements a second time. Each case starts from a four-element list numbered one through four (identifiers one through four).",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 5, "position": 1}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 5, "position": 2}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 5, "position": 3}},
                    {"op": "create", "ref": "d", "attrs": {"parent_id": 5, "position": 4}},
                    {"op": "remove", "ref": "b"}
                ],
                "queries": [
                    {"q": "position_of", "ref": "a"},
                    {"q": "position_of", "ref": "b"},
                    {"q": "position_of", "ref": "c"},
                    {"q": "position_of", "ref": "d"}
                ]
            },
            "expected_output": "position=1\nposition=nil\nposition=2\nposition=3"
        }
    ]
}
```

---

### Feature 12: Deleting a record closes the gap

**As a developer**, I want deleting a list record to automatically close the gap it leaves, so the remaining records stay contiguous.

**Expected Behavior / Usage:**

Deleting a record that is part of the list closes the gap: every element behind the deleted one moves up by a single position so the remaining elements stay contiguously numbered from the top. Deleting more than one element compounds the effect.

**Test Cases:** `rcb_tests/public_test_cases/feature12_delete_closes_gap.json`

```json
{
    "description": "Deleting a record that is part of the list automatically closes the gap: every element that was behind the deleted one moves up by a single position so the remaining elements stay contiguously numbered from the top. Deleting more than one element compounds the effect. Each case starts from a four-element list numbered one through four (identifiers one through four).",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"parent_id": 5, "position": 1}},
                    {"op": "create", "ref": "b", "attrs": {"parent_id": 5, "position": 2}},
                    {"op": "create", "ref": "c", "attrs": {"parent_id": 5, "position": 3}},
                    {"op": "create", "ref": "d", "attrs": {"parent_id": 5, "position": 4}},
                    {"op": "delete", "ref": "b"}
                ],
                "queries": [
                    {"q": "order_ids", "where": {"parent_id": 5}, "order": "position"},
                    {"q": "position_values", "where": {"parent_id": 5}, "order": "position"}
                ]
            },
            "expected_output": "ids=[1, 3, 4]\npositions=[1, 2, 3]"
        }
    ]
}
```

---

### Feature 13: Scoped (partitioned) lists

**As a developer**, I want to partition records into independent sub-lists by one or more grouping keys, so each sub-list is numbered separately.

**Expected Behavior / Usage:**

A list can be partitioned by one or more scope keys so positions are tracked separately within each scope. Records sharing the same scope value(s) form one ordered list numbered from the top; records in a different scope form a wholly separate list with its own independent numbering. The scope can be a single key or a combination of keys (a record belongs to a sub-list only when all scope values match).

**Test Cases:** `rcb_tests/public_test_cases/feature13_scoped_lists.json`

```json
{
    "description": "A list can be partitioned into independent sub-lists by one or more scope keys, so that positions are tracked separately within each scope. Records sharing the same scope key value(s) form one ordered list numbered from the top, and records in a different scope form a wholly separate list with its own independent numbering. The scope can be a single key or a combination of several keys (a record belongs to the same sub-list only when all scope key values match).",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a1", "attrs": {"parent_id": 1, "position": 1}},
                    {"op": "create", "ref": "a2", "attrs": {"parent_id": 1, "position": 2}},
                    {"op": "create", "ref": "a3", "attrs": {"parent_id": 1, "position": 3}},
                    {"op": "create", "ref": "a4", "attrs": {"parent_id": 1, "position": 4}},
                    {"op": "create", "ref": "b1", "attrs": {"parent_id": 2, "position": 1}},
                    {"op": "create", "ref": "b2", "attrs": {"parent_id": 2, "position": 2}},
                    {"op": "create", "ref": "b3", "attrs": {"parent_id": 2, "position": 3}},
                    {"op": "create", "ref": "b4", "attrs": {"parent_id": 2, "position": 4}}
                ],
                "queries": [
                    {"q": "order_ids", "where": {"parent_id": 1}, "order": "position"},
                    {"q": "order_ids", "where": {"parent_id": 2}, "order": "position"},
                    {"q": "position_values", "where": {"parent_id": 1}, "order": "position"},
                    {"q": "position_values", "where": {"parent_id": 2}, "order": "position"}
                ]
            },
            "expected_output": "ids=[1, 2, 3, 4]\nids=[5, 6, 7, 8]\npositions=[1, 2, 3, 4]\npositions=[1, 2, 3, 4]"
        }
    ]
}
```

---

### Feature 14: Move a record across scopes

**As a developer**, I want changing a record's scope key to move it between sub-lists, so both the old and new sub-lists renumber correctly.

**Expected Behavior / Usage:**

When a record's scope key changes, it leaves its old sub-list (which closes the gap to stay contiguous) and joins the target sub-list. Changing the scope key together with an explicit position inserts the record at that position in the destination, shifting the destination's existing elements; changing scope without a position appends it to the end of the destination list.

**Test Cases:** `rcb_tests/public_test_cases/feature14_move_across_scope.json`

```json
{
    "description": "When a record's scope key changes, it leaves its old sub-list and joins the target sub-list. The old sub-list closes the gap left behind so it stays contiguous, and the record takes a position in the new sub-list. Changing the scope key together with an explicit position inserts the record at that position in the destination list, shifting the destination's existing elements; moving a record to another scope without specifying a position appends it to the end of the destination list.",
    "cases": [
        {
            "input": {
                "config": {"column": "position", "scope": "parent_id"},
                "operations": [
                    {"op": "create", "ref": "a1", "attrs": {"parent_id": 1, "position": 1}},
                    {"op": "create", "ref": "a2", "attrs": {"parent_id": 1, "position": 2}},
                    {"op": "create", "ref": "a3", "attrs": {"parent_id": 1, "position": 3}},
                    {"op": "create", "ref": "a4", "attrs": {"parent_id": 1, "position": 4}},
                    {"op": "create", "ref": "b1", "attrs": {"parent_id": 2, "position": 1}},
                    {"op": "create", "ref": "b2", "attrs": {"parent_id": 2, "position": 2}},
                    {"op": "create", "ref": "b3", "attrs": {"parent_id": 2, "position": 3}},
                    {"op": "create", "ref": "b4", "attrs": {"parent_id": 2, "position": 4}},
                    {"op": "update", "ref": "a4", "attrs": {"parent_id": 2, "position": 2}}
                ],
                "queries": [
                    {"q": "order_ids", "where": {"parent_id": 1}, "order": "position"},
                    {"q": "order_ids", "where": {"parent_id": 2}, "order": "position"}
                ]
            },
            "expected_output": "ids=[1, 2, 3]\nids=[5, 4, 6, 7, 8]"
        }
    ]
}
```

---

### Feature 15: Suspend list maintenance

**As a developer**, I want to suspend automatic renumbering for a block of operations, so I can do bulk edits and fix positions myself afterward.

**Expected Behavior / Usage:**

List maintenance can be suspended for a block of operations, so the automatic position adjustments that normally keep the list contiguous are skipped while the raw changes still persist. Within a suspended block, updating one element's position to collide with another does not shuffle the others, and deleting an element does not pull the trailing elements up.

**Test Cases:** `rcb_tests/public_test_cases/feature15_suspend_maintenance.json`

```json
{
    "description": "List maintenance can be suspended for the duration of a block of operations, so that the automatic position adjustments that normally keep the list contiguous are skipped while still persisting the raw changes. Within a suspended block, updating one element's position to collide with another does not shuffle the others, and deleting an element does not pull the trailing elements up. This is used for bulk operations where the caller will fix up positions itself.",
    "cases": [
        {
            "input": {
                "config": {"column": "position"},
                "operations": [
                    {"op": "create", "ref": "a", "attrs": {"position": 1}},
                    {"op": "create", "ref": "b", "attrs": {"position": 2}},
                    {"op": "suspend_maintenance", "operations": [
                        {"op": "update", "ref": "a", "attrs": {"position": 2}}
                    ]}
                ],
                "queries": [
                    {"q": "position_of", "ref": "a"},
                    {"q": "position_of", "ref": "b"}
                ]
            },
            "expected_output": "position=2\nposition=2"
        }
    ]
}
```

---

### Feature 16: Validation of the suspend-maintenance argument

**As a developer**, I want the optional argument to suspend-maintenance validated up front, so a malformed argument fails with a clear, neutral error category.

**Expected Behavior / Usage:**

The suspend-maintenance facility accepts an optional first argument naming additional record types whose maintenance should also be suspended. It must be a collection, and every entry must be a persistable record type. Supplying a non-collection, or a collection containing something that is not a record type, is rejected up front with a neutral categorized error rather than proceeding. The outcome is reported as a normalized error category.

**Test Cases:** `rcb_tests/public_test_cases/feature16_suspend_argument_errors.json`

```json
{
    "description": "The suspend-maintenance facility accepts an optional first argument naming additional record types whose list maintenance should also be suspended. This argument is validated: it must be a collection, and every entry must be a persistable record type. Supplying a value that is not a collection, or a collection containing something that is not a record type, is rejected up front with a neutral, categorized error rather than proceeding. The outcome is reported as a normalized error category.",
    "cases": [
        {
            "input": {
                "config": {"column": "position"},
                "queries": [
                    {"q": "suspend_argument_outcome", "arg": "not_array"}
                ]
            },
            "expected_output": "[a categorization prefix for mismatches]"
        },
        {
            "input": {
                "config": {"column": "position"},
                "queries": [
                    {"q": "suspend_argument_outcome", "arg": "not_record"}
                ]
            },
            "expected_output": "[a categorization prefix for mismatches]"
        }
    ]
}
```

---

### Feature 17: Stepwise shifting under a unique constraint

**As a developer**, I want intermediate shifts to happen one row at a time when the position column is uniquely indexed, so a transient duplicate never violates the constraint.

**Expected Behavior / Usage:**

When the position column is backed by a unique constraint, the intermediate elements are shifted one at a time (stepwise) during a relocation instead of in a single bulk update, so the unique constraint is never transiently violated. This stepwise mode turns on automatically in the presence of a unique index and can be explicitly overridden off. Relocations still produce a contiguous, duplicate-free ordering. A relocation target below the top of the list is rejected with a neutral error.

**Test Cases:** `rcb_tests/public_test_cases/feature17_sequential_updates.json`

```json
{
    "description": "When the position column is backed by a unique constraint, the library shifts intermediate elements one at a time (stepwise) during a relocation instead of in a single bulk update, so the unique constraint is never transiently violated; this stepwise mode turns on automatically in the presence of a unique index and can be explicitly overridden off. Relocations still produce a contiguous, duplicate-free ordering. A relocation target below the top of the list is rejected with a neutral error. Reports cover whether stepwise shuffling is active, the ordering after a relocation, and the rejection of an out-of-range target.",
    "cases": [
        {
            "input": {
                "config": {"column": "pos", "unique": true, "positive": true},
                "queries": [
                    {"q": "stepwise_shuffle"}
                ]
            },
            "expected_output": "stepwise_shuffle=true"
        },
        {
            "input": {
                "config": {"column": "pos", "unique": true, "positive": true, "sequential_updates": false},
                "queries": [
                    {"q": "stepwise_shuffle"}
                ]
            },
            "expected_output": "stepwise_shuffle=false"
        }
    ]
}
```

---

### Feature 18: Timestamp touching on reorder

**As a developer**, I want reordering to refresh the modified-timestamp only of records that actually moved, with the option to disable that touching entirely.

**Expected Behavior / Usage:**

By default, when a reordering changes positions, the modified-timestamp of every record whose position actually changed is refreshed to the current time, while records that did not move keep their earlier timestamp. This touching can be disabled by configuration, in which case a reordering (including gap-closing after a deletion) leaves all timestamps untouched even though positions still update.

**Test Cases:** `rcb_tests/public_test_cases/feature18_touch_timestamps.json`

```json
{
    "description": "By default, when a reordering operation changes positions, the modified-timestamp of every record whose position actually changed is refreshed to the current time, while records that did not move keep their earlier timestamp. This timestamp touching can be disabled by configuration, in which case a reordering (including the gap-closing after a deletion) leaves all timestamps untouched even though positions still update. Each case first creates four elements at a baseline time, then performs one operation at a later time; the report buckets each remaining element's modified-timestamp as either the baseline or the later moment.",
    "cases": [
        {
            "input": {
                "config": {"column": "pos"},
                "operations": [
                    {"op": "at_time", "at": "base", "operations": [
                        {"op": "create", "ref": "a"},
                        {"op": "create", "ref": "b"},
                        {"op": "create", "ref": "c"},
                        {"op": "create", "ref": "d"}
                    ]},
                    {"op": "at_time", "at": "later", "operations": [
                        {"op": "move_down", "ref": "a"}
                    ]}
                ],
                "queries": [
                    {"q": "timestamp_buckets", "order": "id"}
                ]
            },
            "expected_output": "timestamps=[later, later, base, base]"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the list-positioning behavior described above, with configuration, position computation/renumbering, scope partitioning, and persistence hooks kept as distinct logical units.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON command object from stdin, applies the `operations`, evaluates the `queries`, and prints the result to stdout, strictly matching the per-feature contracts above. It must be logically (and ideally physically) separated from the core domain, and is solely responsible for normalizing any raised error into the neutral `error=<category>` lines.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`, containing only the raw stdout from the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the standard delimiter defined in the Readme for list parsing
- refer to the 'timestamp mode' when touch is disabled
