## Product Requirement Document

# Memory Allocation Contract Toolkit - Deterministic Allocation Behavior Adapter

## Project Goal

Build a memory allocation contract toolkit that allows developers to request, resize, align, classify, and inspect memory allocations through a deterministic execution adapter without depending on process-specific pointer values or allocator-internal diagnostics.

---

## Background & Problem

Without this library/tool, developers are forced to validate allocation behavior by reading raw pointers, platform-specific error values, and ad hoc test binaries. This leads to brittle tests, hard-to-compare output, and false confidence when pointer addresses or host-runtime details change between environments.

With this library/tool, allocation behavior is exposed as stable input/output contracts: callers provide JSON data describing the allocation scenario, and the adapter prints normalized stdout fields describing observable allocation results, sizing decisions, alignment behavior, and lifecycle outcomes.

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

### Feature 1: Allocation Size Calculations

**As a developer**, I want to understand how byte requests are classified and rounded, so I can predict the amount of memory that will be made usable for a request.

**Expected Behavior / Usage:**

*1.1 Allocation Bucket Ranges — Map requested byte counts to deterministic usable-size buckets.*

A request is supplied as an object containing `requested_bytes`. The adapter prints the request, the bucket index selected for that request, and, for nonzero requests, the inclusive byte range covered by that bucket and the usable byte count at the top of the range. A zero-byte request has a defined sentinel bucket index and does not print a byte range.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_size_class_ranges.json`

```json
{
    "description": "Maps a requested allocation size to the allocation bucket that covers it, reporting the bucket index and byte range for nonzero requests.",
    "cases": [
        {
            "input": {"requested_bytes": 0},
            "expected_output": "requested_bytes=0\nclass_index=235\n"
        },
        {
            "input": {"requested_bytes": 1},
            "expected_output": "requested_bytes=1\nclass_index=0\nrange_start=1\nusable_bytes=16\n"
        },
        {
            "input": {"requested_bytes": 17},
            "expected_output": "requested_bytes=17\nclass_index=1\nrange_start=17\nusable_bytes=32\n"
        },
        {
            "input": {"requested_bytes": 129},
            "expected_output": "requested_bytes=129\nclass_index=8\nrange_start=129\nusable_bytes=160\n"
        },
        {
            "input": {"requested_bytes": 65537},
            "expected_output": "requested_bytes=65537\nclass_index=44\nrange_start=65537\nusable_bytes=81920\n"
        }
    ]
}
```

*1.2 Alignment Rounding — Round requested byte counts for a required alignment.*

A request is supplied as an object containing `alignment_bytes` and `requested_bytes`. The adapter prints the alignment, the original requested byte count, and the rounded byte count. The rounded value must never be smaller than the request and must satisfy the requested alignment.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_alignment_rounding.json`

```json
{
    "description": "Rounds a requested byte count up to a size that satisfies a requested power-of-two alignment without shrinking the request.",
    "cases": [
        {
            "input": {"alignment_bytes": 128, "requested_bytes": 160},
            "expected_output": "alignment_bytes=128\nrequested_bytes=160\nrounded_bytes=256\n"
        },
        {
            "input": {"alignment_bytes": 64, "requested_bytes": 65},
            "expected_output": "alignment_bytes=64\nrequested_bytes=65\nrounded_bytes=128\n"
        },
        {
            "input": {"alignment_bytes": 1, "requested_bytes": 65},
            "expected_output": "alignment_bytes=1\nrequested_bytes=65\nrounded_bytes=65\n"
        },
        {
            "input": {"alignment_bytes": 4096, "requested_bytes": 4097},
            "expected_output": "alignment_bytes=4096\nrequested_bytes=4097\nrounded_bytes=8192\n"
        }
    ]
}
```

---

### Feature 2: Allocation Operations

**As a developer**, I want standard allocation operations to produce normalized observable results, so I can verify success, usable capacity, alignment, zero-initialization, resizing, and error handling without inspecting raw addresses.

**Expected Behavior / Usage:**

*2.1 Basic Allocation — Allocate a single block by requested byte count.*

A request is supplied as an object containing `requested_bytes`. The adapter prints the requested byte count, the alignment contract used for the basic allocation, a normalized `error` value, whether the result is `allocated` or `null`, and, on success, the usable byte count and alignment remainder. Successful allocations must have `error=none` and `alignment_remainder=0`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_basic_allocation.json`

```json
{
    "description": "Allocates a requested number of bytes and reports whether the allocation succeeded, the usable size, and the alignment remainder of the returned block.",
    "cases": [
        {
            "input": {"requested_bytes": 16},
            "expected_output": "requested_bytes=16\nalignment_bytes=1\nerror=none\nresult=allocated\nusable_bytes=16\nalignment_remainder=0\n"
        }
    ]
}
```

*2.2 Zero-Initialized Allocation — Allocate an array-style block whose requested bytes are zeroed.*

A request is supplied as an object containing `element_count` and `element_bytes`. The adapter prints the element inputs, total requested byte count, allocation metadata, and, on success, the number of requested bytes observed as zero-filled. Zero-element requests still return an allocated block with zero requested bytes and `zero_filled_bytes=0`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_zero_initialized_allocation.json`

```json
{
    "description": "Allocates an array-style block and reports both allocation metadata and how many requested bytes are zero-initialized.",
    "cases": [
        {
            "input": {"element_count": 5, "element_bytes": 16},
            "expected_output": "element_count=5\nelement_bytes=16\nrequested_bytes=80\nalignment_bytes=1\nerror=none\nresult=allocated\nusable_bytes=80\nalignment_remainder=0\nzero_filled_bytes=80\n"
        },
        {
            "input": {"element_count": 0, "element_bytes": 16},
            "expected_output": "element_count=0\nelement_bytes=16\nrequested_bytes=0\nalignment_bytes=1\nerror=none\nresult=allocated\nusable_bytes=16\nalignment_remainder=0\nzero_filled_bytes=0\n"
        },
        {
            "input": {"element_count": 0, "element_bytes": 0},
            "expected_output": "element_count=0\nelement_bytes=0\nrequested_bytes=0\nalignment_bytes=1\nerror=none\nresult=allocated\nusable_bytes=16\nalignment_remainder=0\nzero_filled_bytes=0\n"
        }
    ]
}
```

*2.3 Resize Allocation — Resize an existing or missing allocation.*

A request is supplied as an object containing `initial_allocation_bytes` and `target_bytes`. `initial_allocation_bytes` may be a byte count or the string `none` to represent a missing initial block. The adapter prints the initial allocation descriptor, target request, basic alignment contract, normalized error category, and allocation result. Resizing to zero returns `result=null` with no error. Resizing a missing allocation to a normal size behaves like a fresh allocation. An impossible maximum-size request is reported as `error=out_of_memory` with `result=null`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_resize_allocation.json`

```json
{
    "description": "Resizes either an existing allocation or a missing allocation, reporting the normalized result for zero-size, normal-size, and impossible-size requests.",
    "cases": [
        {
            "input": {"initial_allocation_bytes": 16, "target_bytes": 0},
            "expected_output": "initial_allocation=16\nrequested_bytes=0\nalignment_bytes=1\nerror=none\nresult=null\n"
        },
        {
            "input": {"initial_allocation_bytes": "none", "target_bytes": 48},
            "expected_output": "initial_allocation=none\nrequested_bytes=48\nalignment_bytes=1\nerror=none\nresult=allocated\nusable_bytes=48\nalignment_remainder=0\n"
        },
        {
            "input": {"initial_allocation_bytes": 80, "target_bytes": 80},
            "expected_output": "initial_allocation=80\nrequested_bytes=80\nalignment_bytes=1\nerror=none\nresult=allocated\nusable_bytes=80\nalignment_remainder=0\n"
        },
        {
            "input": {"initial_allocation_bytes": 16, "target_bytes": "max"},
            "expected_output": "initial_allocation=16\nrequested_bytes=[a failure condition for excessive targets — check the max_u64 constant for the specific value]\nalignment_bytes=1\nerror=out_of_memory\nresult=null\n"
        }
    ]
}
```

*2.4 Explicitly Aligned Allocation — Allocate with caller-provided alignment.*

A request is supplied as an object containing `alignment_bytes` and `requested_bytes`. The adapter prints the request, alignment, normalized error category, and allocation result. Valid alignments return allocated blocks whose address remainder for that alignment is zero, including zero-byte allocation requests. Invalid alignments are normalized as `error=invalid_argument` and produce `result=null`. Impossible allocation sizes are normalized as `error=out_of_memory` and produce `result=null`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_aligned_allocation.json`

```json
{
    "description": "Requests an allocation with an explicit alignment and reports allocation metadata or a normalized error for invalid alignment and impossible size inputs.",
    "cases": [
        {
            "input": {"alignment_bytes": 8, "requested_bytes": 16},
            "expected_output": "requested_bytes=16\nalignment_bytes=8\nerror=none\nresult=allocated\nusable_bytes=16\nalignment_remainder=0\n"
        },
        {
            "input": {"alignment_bytes": 8, "requested_bytes": 0},
            "expected_output": "requested_bytes=0\nalignment_bytes=8\nerror=none\nresult=allocated\nusable_bytes=16\nalignment_remainder=0\n"
        },
        {
            "input": {"alignment_bytes": 0, "requested_bytes": 4096},
            "expected_output": "requested_bytes=4096\nalignment_bytes=0\nerror=invalid_argument\nresult=null\n"
        },
        {
            "input": {"alignment_bytes": 4, "requested_bytes": 4096},
            "expected_output": "requested_bytes=4096\nalignment_bytes=4\nerror=invalid_argument\nresult=null\n"
        },
        {
            "input": {"alignment_bytes": 9, "requested_bytes": 0},
            "expected_output": "requested_bytes=0\nalignment_bytes=9\nerror=invalid_argument\nresult=null\n"
        },
        {
            "input": {"alignment_bytes": 8, "requested_bytes": "max"},
            "expected_output": "requested_bytes=[a failure condition for excessive targets — check the max_u64 constant for the specific value]\nalignment_bytes=8\nerror=out_of_memory\nresult=null\n"
        }
    ]
}
```

---

### Feature 3: Allocation Introspection and Lifecycle

**As a developer**, I want to inspect allocated blocks and lifecycle state through stable summaries, so I can verify that interior pointers resolve correctly and that allocation/deallocation sequences do not leak live objects.

**Expected Behavior / Usage:**

*3.1 External Pointer Lookup — Resolve an interior offset to allocation boundaries.*

A request is supplied as an object containing `allocation_bytes` and `interior_offset`. The adapter allocates a block, treats the supplied offset as an interior location, and prints the request as `requested_bytes`, the interior offset, the resolved start offset, the resolved end offset, and usable bytes. The resolved start of any valid interior location must be offset `0`, and the resolved end offset must be the last byte of the usable allocation.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_external_pointer_lookup.json`

```json
{
    "description": "Given an interior offset within an allocated block, resolves the allocation start and end positions relative to the original block.",
    "cases": [
        {
            "input": {"allocation_bytes": 160, "interior_offset": 34},
            "expected_output": "requested_bytes=160\ninterior_offset=34\nstart_offset=0\nend_offset=159\nusable_bytes=160\n"
        },
        {
            "input": {"allocation_bytes": 16, "interior_offset": 0},
            "expected_output": "requested_bytes=16\ninterior_offset=0\nstart_offset=0\nend_offset=15\nusable_bytes=16\n"
        },
        {
            "input": {"allocation_bytes": 16, "interior_offset": 15},
            "expected_output": "requested_bytes=16\ninterior_offset=15\nstart_offset=0\nend_offset=15\nusable_bytes=16\n"
        }
    ]
}
```

*3.2 Allocation Lifecycle — Verify uniqueness of live allocations and empty state after deallocation.*

A request is supplied as an object containing `allocation_count` and `object_bytes`. The adapter allocates the requested number of same-sized live objects, verifies that no two live objects share the same address, deallocates all of them, and prints the allocation count, object size, whether live allocations were unique, and whether the pool is empty after all deallocations.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_allocation_lifecycle.json`

```json
{
    "description": "Allocates many same-sized live objects, checks that live objects are distinct, deallocates them, and reports whether the allocation pool is empty afterward.",
    "cases": [
        {
            "input": {"allocation_count": 32, "object_bytes": 20},
            "expected_output": "allocation_count=32\nobject_bytes=20\nunique_live_allocations=yes\npool_empty_after_deallocate=yes\n"
        },
        {
            "input": {"allocation_count": 128, "object_bytes": 16},
            "expected_output": "allocation_count=128\nobject_bytes=16\nunique_live_allocations=yes\npool_empty_after_deallocate=yes\n"
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
- follow the same bucket selection logic used in the size classes module
- validate the offset bounds as defined in the external pointer lookup helper
