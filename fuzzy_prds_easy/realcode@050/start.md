## Product Requirement Document

# ORM Query Result Cache - Black-Box Behavior Contract

## Project Goal

Build an ORM-integrated result caching library that allows developers to reuse repeated query, raw-query, template-fragment, and dependency-based computed results without manually managing cache keys, relationship invalidation, or per-query cache policy.

---

## Background & Problem

Without this library/tool, developers are forced to manually wrap every repeated ORM read, rendered fragment, and expensive computed value with ad hoc cache-key generation and explicit invalidation. This leads to stale records, duplicated query logic, inconsistent handling of related objects, and fragile behavior when locale or database context changes.

With this library/tool, repeated reads can be cached through normal ORM and template usage, while saves and relationship changes invalidate affected cached values automatically.

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

### Feature 1: Read Query Result Caching

**As a developer**, I want to run common read operations repeatedly, so I can avoid duplicate storage reads while preserving normal record and list results.

**Expected Behavior / Usage:**

This feature group covers the leaf behaviors below. Each leaf accepts a JSON command describing the black-box scenario and prints newline-delimited signals containing the storage context, operation type, returned data, and cache-observable state.

*1.1 Single-record lookup caching — A primary-key style lookup returns the requested record fields*

A primary-key style lookup returns the requested record fields. When the same lookup is evaluated again in the same application context, the observable record data stays unchanged and the cache-state signal changes from storage-backed to cache-backed.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_single_record_lookup.json`

```json
{
    "description": "A repeated primary-key record lookup should return the same record data while exposing that the first ORM lookup came from storage and the second lookup came from cache.",
    "cases": [
        {
            "input": {
                "scenario": "single_record_lookup",
                "selector": {
                    "id": 1
                }
            },
            "expected_output": "database=default\nlookup=single_record\nfirst=id=1 val=42 from_cache=false\nsecond=id=1 val=42 from_cache=true\n"
        }
    ]
}
```

*1.2 Filtered list lookup caching — A filtered list lookup returns its count and record data*

A filtered list lookup returns its count and record data. Repeating the same filter returns the same list contents while exposing that the second evaluation is served from cache.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_filtered_list_lookup.json`

```json
{
    "description": "A repeated filtered list lookup should return one matching record and expose cache-state metadata for each evaluation.",
    "cases": [
        {
            "input": {
                "scenario": "filtered_list_lookup",
                "selector": {
                    "id": 1
                }
            },
            "expected_output": "database=default\nlookup=filtered_list\nfirst_count=1\nfirst_0=id=1 val=42 from_cache=false\nsecond_count=1\nsecond_0=id=1 val=42 from_cache=true\n"
        }
    ]
}
```

*1.3 Sliced list lookup caching — A filtered lookup with a result slice returns the requested slice and count*

A filtered lookup with a result slice returns the requested slice and count. Repeating the same sliced lookup returns identical record data while exposing cache-backed evaluation.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_sliced_list_lookup.json`

```json
{
    "description": "A repeated sliced filtered lookup should return the requested slice and expose cache-state metadata for each evaluation.",
    "cases": [
        {
            "input": {
                "scenario": "sliced_list_lookup",
                "selector": {
                    "id": 1
                }
            },
            "expected_output": "database=default\nlookup=sliced_list\nfirst_count=1\nfirst_0=id=1 val=42 from_cache=false\nsecond_count=1\nsecond_0=id=1 val=42 from_cache=true\n"
        }
    ]
}
```

*1.4 Raw table lookup caching — A raw table query routed through the ORM returns record fields and participates in the same cache-state contract as normal ORM reads*

A raw table query routed through the ORM returns record fields and participates in the same cache-state contract as normal ORM reads. The output includes the lookup type, count, record fields, and from-cache signal.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_raw_sql_lookup.json`

```json
{
    "description": "A repeated raw table lookup should return the selected record fields and expose whether each raw result came from storage or cache.",
    "cases": [
        {
            "input": {
                "scenario": "raw_table_lookup",
                "selector": {
                    "id": 1
                }
            },
            "expected_output": "database=default\nlookup=raw_table\nfirst_count=1\nfirst_0=id=1 val=42 from_cache=false\nsecond_count=1\nsecond_0=id=1 val=42 from_cache=true\n"
        }
    ]
}
```

*1.5 Parameterized raw lookup identity — Parameterized raw lookups must include parameter values in their cache identity*

Parameterized raw lookups must include parameter values in their cache identity. Different identifier parameters return their corresponding records rather than reusing a cached result for a previous parameter.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_parameterized_raw_lookup.json`

```json
{
    "description": "Parameterized raw lookups should include parameter values in the cache identity so different identifiers return their own records.",
    "cases": [
        {
            "input": {
                "scenario": "raw_parameter_lookup",
                "selector": {
                    "ids": [
                        1,
                        2
                    ]
                }
            },
            "expected_output": "database=default\nlookup=raw_parameterized\nparam_0=1 count=1 id=1 val=42 from_cache=false\nparam_1=2 count=1 id=2 val=42 from_cache=false\n"
        }
    ]
}
```

---

### Feature 2: Invalidation After Record Changes

**As a developer**, I want to keep cached reads coherent after writes, so I can trust cached reads after related data changes.

**Expected Behavior / Usage:**

This feature group covers the leaf behaviors below. Each leaf accepts a JSON command describing the black-box scenario and prints newline-delimited signals containing the storage context, operation type, returned data, and cache-observable state.

*2.1 Saved record invalidates its cached reads — After a record has populated single-record and list-query caches, saving that record invalidates both cache entries*

After a record has populated single-record and list-query caches, saving that record invalidates both cache entries. The next reads return the same record data but expose storage-backed cache-state signals, and subsequent reads can be cached again.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_record_save_invalidation.json`

```json
{
    "description": "Saving a cached record should invalidate cached single-record and list-query results for that record, and later reads should be recached.",
    "cases": [
        {
            "input": {
                "scenario": "object_save_invalidation"
            },
            "expected_output": "database=default\ninvalidation=record_save\nsingle_before=false\nlist_before=false\nsingle_cached=true\nlist_cached=true\nsingle_after_save=false\nlist_after_save=false\nsingle_recached=true\nlist_recached=true\n"
        }
    ]
}
```

*2.2 Cross-locale save invalidates default-locale reads — Cache invalidation is not limited to the currently active locale*

Cache invalidation is not limited to the currently active locale. If a record is read in the default locale, then read and saved while an alternate locale is active, returning to the default locale and reading again must expose fresh storage-backed reads.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_cross_locale_invalidation.json`

```json
{
    "description": "Saving a record while an alternate locale is active should invalidate cached results that were originally read in the default locale.",
    "cases": [
        {
            "input": {
                "scenario": "cross_locale_invalidation"
            },
            "expected_output": "database=default\ninvalidation=cross_locale_record_save\ndefault_single_before=false\ndefault_list_before=false\ndefault_single_cached=true\ndefault_list_cached=true\nalternate_locale=fr\nalternate_single_cached=true\nalternate_list_cached=true\ndefault_single_after_alternate_save=false\ndefault_list_after_alternate_save=false\n"
        }
    ]
}
```

*2.3 Child save invalidates related records — When a cached child record references another record, saving the child invalidates the referenced record cache*

When a cached child record references another record, saving the child invalidates the referenced record cache. A subsequent lookup of the referenced record exposes a storage-backed read rather than stale cached data.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_related_child_save_invalidation.json`

```json
{
    "description": "Saving a child record should invalidate cache entries for related records referenced by that child.",
    "cases": [
        {
            "input": {
                "scenario": "child_save_invalidates_related"
            },
            "expected_output": "database=default\ninvalidation=child_save_to_related_record\nchild_before_save_from_cache=false\nrelated_before_save=id=2 name=clouseroo from_cache=false\nrelated_after_child_save=id=2 name=clouseroo from_cache=false\n"
        }
    ]
}
```

*2.4 Related record update invalidates parent records — When a related record changes, cached parent records that include that relation are invalidated*

When a related record changes, cached parent records that include that relation are invalidated. The next parent lookup exposes a storage-backed read and includes the updated related value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_related_parent_update_invalidation.json`

```json
{
    "description": "Updating a related record should invalidate cached parent records that include that relation and expose the updated related value on the next parent read.",
    "cases": [
        {
            "input": {
                "scenario": "related_update_invalidates_parent"
            },
            "expected_output": "database=default\ninvalidation=related_record_update_to_parent\nparent_before=false\nparent_cached=true\nrelated_before_update=id=2 name=clouseroo from_cache=true\nrelated_after_update=id=2 name=fffuuu from_cache=false\nparent_after_related_update=id=1 val=42 related_name=fffuuu from_cache=false\n"
        }
    ]
}
```

*2.5 Reverse relation membership invalidation — A cached empty reverse relation must not remain stale when matching child records are created*

A cached empty reverse relation must not remain stale when matching child records are created. Later reverse lookups include newly created members in insertion order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_reverse_relation_membership_invalidation.json`

```json
{
    "description": "A cached empty reverse relation should be invalidated when matching child records are created so later reverse lookups include the new members.",
    "cases": [
        {
            "input": {
                "scenario": "reverse_relation_invalidation"
            },
            "expected_output": "database=default\ninvalidation=reverse_relation_membership\ninitial_values=[]\nafter_first_create_values=[42]\nafter_second_create_values=[42, 17]\n"
        }
    ]
}
```

---

### Feature 3: Template Fragment Caching

**As a developer**, I want to cache rendered template fragments keyed by records or queries, so I can avoid rerendering expensive fragments while still refreshing changed content.

**Expected Behavior / Usage:**

This feature group covers the leaf behaviors below. Each leaf accepts a JSON command describing the black-box scenario and prints newline-delimited signals containing the storage context, operation type, returned data, and cache-observable state.

*3.1 List-based template fragment — A template fragment keyed by a record list renders the list contents, can be reused on a repeated render, and refreshes after one member record is saved with changed data*

A template fragment keyed by a record list renders the list contents, can be reused on a repeated render, and refreshes after one member record is saved with changed data.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_query_template_fragment.json`

```json
{
    "description": "A cached template fragment based on a record list should render the list contents, reuse the fragment, and refresh after a member record changes.",
    "cases": [
        {
            "input": {
                "scenario": "template_queryset_fragment"
            },
            "expected_output": "template_engine=jinja\nfragment=queryset\nfirst_render=1:42;2:42;\nsecond_render=1:42;2:42;\nafter_record_save_render=[a specific slice content pattern reflecting boolean cache hits/misses];\nrecached_render=[a specific slice content pattern reflecting boolean cache hits/misses];\n"
        }
    ]
}
```

*3.2 Record-based template fragment — A template fragment keyed by a single record renders that record content and refreshes after the same record is saved with changed data*

A template fragment keyed by a single record renders that record content and refreshes after the same record is saved with changed data.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_object_template_fragment.json`

```json
{
    "description": "A cached template fragment based on one record should render record content and refresh when that record is saved with changed data.",
    "cases": [
        {
            "input": {
                "scenario": "template_object_fragment"
            },
            "expected_output": "template_engine=jinja\nfragment=single_record\nfirst_render=1:42\nafter_record_save_render=1:17\n"
        }
    ]
}
```

*3.3 Multiple fragments in one template — Multiple cache blocks in one template are cached independently*

Multiple cache blocks in one template are cached independently. When the shared record changes, each block refreshes to reflect its own portion of the new record state.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_multiple_template_fragments.json`

```json
{
    "description": "Multiple cached fragments in one template should be cached independently and all refresh after their shared record changes.",
    "cases": [
        {
            "input": {
                "scenario": "template_multiple_fragments"
            },
            "expected_output": "template_engine=jinja\nfragment=multiple_blocks\n[the variable prefixes corresponding to the start/end of a cached template block]\n1\n42\nfirst_render_end\n[the variable prefixes corresponding to the start/end of a cached template block]\n1\n17\nafter_record_save_render_end\n"
        }
    ]
}
```

*3.4 Extra fragment key values — A template fragment may include an additional key value*

A template fragment may include an additional key value. Different extra-key values produce distinct cached fragments, both when no explicit timeout is supplied and when a timeout is supplied.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_template_fragment_extra_key.json`

```json
{
    "description": "Template fragments that include an extra key should keep distinct cached values for distinct extra-key values, with or without an explicit timeout.",
    "cases": [
        {
            "input": {
                "scenario": "template_extra_key_fragments"
            },
            "expected_output": "template_engine=jinja\nfragment=extra_key\nwithout_timeout_extra_1=1:1\nwithout_timeout_extra_2=1:2\nwith_timeout_extra_1=1:1\nwith_timeout_extra_2=1:2\n"
        }
    ]
}
```

---

### Feature 4: Computed Value Caching

**As a developer**, I want to cache computed values that depend on records or queries, so I can avoid re-running expensive computations while preserving dependency invalidation.

**Expected Behavior / Usage:**

This feature group covers the leaf behaviors below. Each leaf accepts a JSON command describing the black-box scenario and prints newline-delimited signals containing the storage context, operation type, returned data, and cache-observable state.

*4.1 Dependency-aware computed values — A computed value associated with a record or query is reused for repeated calls until its dependency is saved*

A computed value associated with a record or query is reused for repeated calls until its dependency is saved. Locale-specific computed values are isolated from each other and are recomputed independently.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_dependent_value_cache.json`

```json
{
    "description": "A computed value associated with a record or query should be reused until its dependency changes, and locale-specific values should not overwrite each other.",
    "cases": [
        {
            "input": {
                "scenario": "helper_cached_value",
                "mode": "record_and_query"
            },
            "expected_output": "helper=dependent_value_cache\nrecord_call_1=1\nrecord_call_2=1\nrecord_call_alternate_locale=2\nrecord_call_after_save_alternate_locale=3\nrecord_call_default_locale_after_restore=4\nquery_call_1=1\nquery_call_2=1\nquery_call_after_save=2\nquery_call_after_save_repeat=2\n"
        }
    ]
}
```

*4.2 Computed values with missing or non-ASCII dependency keys — Computed value caching remains usable when the dependency has no cache key or when the dependency key contains non-ASCII text*

Computed value caching remains usable when the dependency has no cache key or when the dependency key contains non-ASCII text. The output reports the normalized dependency-key condition and computed result.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_dependent_value_edge_keys.json`

```json
{
    "description": "Computed value caching should still return values when the dependency has no cache key or when the dependency key contains non-ASCII text.",
    "cases": [
        {
            "input": {
                "scenario": "helper_cached_value",
                "mode": "missing_dependency_key"
            },
            "expected_output": "helper=dependent_value_cache\ndependency_key=missing\nresult=1\n"
        },
        {
            "input": {
                "scenario": "helper_cached_value",
                "mode": "unicode_key"
            },
            "expected_output": "helper=dependent_value_cache\ndependency_key=unicode\nresult=1\n"
        }
    ]
}
```

*4.3 Record method result caching — A cached record-bound computation memoizes by record instance and argument*

A cached record-bound computation memoizes by record instance and argument. Saving the same instance does not clear its local memoized value, fresh instances can reuse stored values, new arguments compute separately, and method documentation remains available.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_record_method_value_cache.json`

```json
{
    "description": "A cached record method should memoize by instance and argument, preserve method documentation, and reuse cached argument values on fresh instances.",
    "cases": [
        {
            "input": {
                "scenario": "instance_method_value_cache"
            },
            "expected_output": "helper=record_method_value_cache\nsame_instance_default_1=arg=1 call_count=1\nsame_instance_default_2=arg=1 call_count=1\nsame_instance_after_save=arg=1 call_count=1\nsame_instance_arg_3=arg=3 call_count=2\nfresh_instance_default=arg=1 call_count=3\nfresh_instance_arg_4=arg=4 call_count=4\nfresh_instance_arg_3=arg=3 call_count=2\nother_record_default=arg=1 call_count=5\ndocumentation_preserved=true\n"
        }
    ]
}
```

---

### Feature 5: Cache Policy Controls and Boundaries

**As a developer**, I want to control when queries cache and isolate caches across boundaries, so I can choose correctness and performance behavior per query context.

**Expected Behavior / Usage:**

This feature group covers the leaf behaviors below. Each leaf accepts a JSON command describing the black-box scenario and prints newline-delimited signals containing the storage context, operation type, returned data, and cache-observable state.

*5.1 Per-query cache directives — A query can explicitly bypass caching, opt back into caching with a timeout, or derive a non-caching query from a caching query*

A query can explicitly bypass caching, opt back into caching with a timeout, or derive a non-caching query from a caching query. The most recent directive determines whether the resulting read exposes cache metadata.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_query_cache_controls.json`

```json
{
    "description": "Per-query cache directives should allow bypassing caching, setting explicit timeouts, and making the most recent directive determine caching behavior.",
    "cases": [
        {
            "input": {
                "scenario": "query_cache_controls",
                "mode": "last_directive_wins"
            },
            "expected_output": "database=default\ncache_control=last_directive_wins\ncached_query_timeout=12\nderived_no_cache_timeout=[the specific negative integer value used to denote '[the specific negative integer value used to denote 'absent' or 'no' cache return]' or 'no' cache return]\nderived_no_cache_record=id=1 val=42 from_cache=[the specific negative integer value used to denote 'absent' or 'no' cache return]\ncached_query_record=id=1 val=42 from_cache_present=true\n"
        }
    ]
}
```

*5.2 Empty result caching policy — Empty query results are not cached by default and therefore execute storage reads on repeated evaluation*

Empty query results are not cached by default and therefore execute storage reads on repeated evaluation. When empty-result caching is enabled, the second evaluation returns the same empty length without a storage query.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_empty_queryset_caching.json`

```json
{
    "description": "Empty query results should normally be fetched again on repeated evaluation but should avoid the second SQL query when empty-result caching is enabled.",
    "cases": [
        {
            "input": {
                "scenario": "empty_queryset_behavior",
                "mode": "cache_empty"
            },
            "expected_output": "database=default\nempty_queryset=cache_empty\nfirst_length=0\nfirst_sql_queries=1\nsecond_length=0\nsecond_sql_queries=0\n"
        }
    ]
}
```

*5.3 Multi-database cache isolation — The same lookup evaluated against different database aliases maintains separate cache entries*

The same lookup evaluated against different database aliases maintains separate cache entries. A repeated default-database lookup may be cache-backed, but the first secondary-database lookup remains storage-backed and reports its own database alias.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_multidatabase_cache_isolation.json`

```json
{
    "description": "The same lookup on different database aliases should maintain separate cache entries so a secondary database read is not satisfied from the default database cache.",
    "cases": [
        {
            "input": {
                "scenario": "multidatabase_cache_isolation"
            },
            "expected_output": "lookup=multi_database\ndefault_first=id=1 val=42 db=default from_cache=false\ndefault_second=id=1 val=42 db=default from_cache=true\nsecondary_first=id=1 val=42 db=slave from_cache=false\n"
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
- mimics the valid dependency key constraint structure and returns the associated error marker string
- uses the causal dependency key binding and returns the corresponding valid lookup result
