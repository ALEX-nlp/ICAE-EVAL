## Product Requirement Document

# ORM Slug Automation - Generate Persistent URL Identifiers for Records

## Project Goal

Build a record slugging library that allows developers to automatically create stable, readable, URL-safe identifiers from model data without hand-writing normalization, uniqueness checks, update rules, lookup helpers, and persistence integration for every record type.

---

## Background & Problem

Without this library/tool, developers are forced to manually normalize text, handle duplicate slugs, decide how updates affect existing URLs, account for deleted records, and write lookup code around persisted records. This leads to repetitive code, broken links, inconsistent transliteration, and subtle bugs when records collide or change over time.

With this library/tool, developers declare how record fields produce slugs and rely on the system to generate, persist, update, and query those slugs consistently through normal record lifecycle operations.

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

### Feature 1: Basic Slug Normalization

**As a developer**, I want to create records with URL-safe identifiers derived from visible text, so I can link and query records using stable readable strings.

**Expected Behavior / Usage:**

When the adapter receives a record-creation input containing a slug profile, source text, and optional existing slug value, it saves one record through the persistence layer and prints the workflow name, assigned record identifier, persisted record count, original title, generated slug, stored slug, and any secondary slug field. Text is lowercased, accents and unsupported punctuation are transliterated or removed, whitespace is trimmed, separators are inserted between words, empty source text produces a null slug, and false-like scalar source values still produce explicit slug strings when they represent visible values.

**Test Cases:** `rcb_tests/public_test_cases/feature1_basic_slug_normalization.json`

```json
{
    "description": "Creating a record with a slug-enabled text field normalizes visible source content into a stored URL-safe slug while preserving the record data.",
    "cases": [
        {
            "input": {
                "workflow": "create_record",
                "kind": "standard",
                "title": "My First Post"
            },
            "expected_output": "workflow=create_record\nrecord_id=1\nrecord_count=1\ntitle=My First Post\nslug=my-first-post\nstored_slug=my-first-post\nsecondary_slug=<null>\n"
        }
    ]
}
```

---

### Feature 2: Multi-Value and Associated Sources

**As a developer**, I want to compose slugs from more than one input value or from an associated record, so I can avoid duplicating source-concatenation code in each record workflow.

**Expected Behavior / Usage:**

The input may provide multiple source fields or an associated owner record plus a title. The output must show that the saved record went through the persistence workflow and that the slug is built from all available source values in order. If an associated source is missing, the generated slug uses only the available source values rather than failing.

**Test Cases:** `rcb_tests/public_test_cases/feature2_multi_value_and_relation_sources.json`

```json
{
    "description": "Slug generation can combine multiple supplied values or an associated record value with the main source value, omitting missing associated values.",
    "cases": [
        {
            "input": {
                "workflow": "create_record",
                "kind": "multiple_sources",
                "title": "A Post Title",
                "subtitle": "A Subtitle"
            },
            "expected_output": "workflow=create_record\nrecord_id=1\nrecord_count=1\ntitle=A Post Title\nslug=[a configured max length threshold]-title-a-subtitle\nstored_slug=[a configured max length threshold]-title-a-subtitle\nsecondary_slug=<null>\n"
        }
    ]
}
```

---

### Feature 3: Multiple Slug Outputs and Primary Slug Key

**As a developer**, I want to generate more than one slug field for the same saved record, so I can support records that expose different URL identifiers for different contexts.

**Expected Behavior / Usage:**

The input describes a record creation profile with separate source values for primary and secondary slug outputs. The adapter must print both the normal slug and the secondary slug when the saved record has both fields. A primary slug key lookup profile must report which slug field is treated as the main lookup key and the value stored in that field.

**Test Cases:** `rcb_tests/public_test_cases/feature3_custom_output_fields.json`

```json
{
    "description": "A single saved record can produce multiple independent slug fields from different source values and separators.",
    "cases": [
        {
            "input": {
                "workflow": "create_record",
                "kind": "multiple_outputs",
                "title": "My Test Post",
                "subtitle": "My Subtitle"
            },
            "expected_output": "workflow=create_record\nrecord_id=1\nrecord_count=1\ntitle=My Test Post\nslug=my-test-post\nstored_slug=my-test-post\nsecondary_slug=my.subtitle\n"
        }
    ]
}
```

---

### Feature 4: Separator and Transformation Profiles

**As a developer**, I want to apply alternate slug formatting profiles, so I can match different URL or routing conventions without changing record data.

**Expected Behavior / Usage:**

The input selects a formatting profile and source text. The output must show the saved record and the slug produced by that profile. Profiles can change the word separator, remove separators entirely, reverse or otherwise transform the normalized string, preserve configured characters, or apply language-specific transliteration rules; the contract is the exact slug printed in stdout.

**Test Cases:** `rcb_tests/public_test_cases/feature4_separators_and_transform_profiles.json`

```json
{
    "description": "Slug generation supports alternate separator and transformation profiles while still returning the persisted slug for the saved record.",
    "cases": [
        {
            "input": {
                "workflow": "create_record",
                "kind": "custom_separator",
                "title": "A post title"
            },
            "expected_output": "workflow=create_record\nrecord_id=1\nrecord_count=1\ntitle=A post title\nslug=a.post.title\nstored_slug=a.post.title\nsecondary_slug=<null>\n"
        }
    ]
}
```

---

### Feature 5: Length-Limited Slugs

**As a developer**, I want to limit generated slug length, so I can fit identifiers into constrained database fields and URL policies.

**Expected Behavior / Usage:**

The input selects a length-limited profile and source text. The output must show the saved record and a slug that respects the configured limit. One profile truncates at a word boundary when possible, another permits exact character cuts; when multiple records collide under the same limit, uniqueness suffixes are appended after the truncated base.

**Test Cases:** `rcb_tests/public_test_cases/feature5_length_limits.json`

```json
{
    "description": "Configured maximum slug lengths are enforced either at word boundaries or by exact character truncation, and suffixes are appended when collisions occur.",
    "cases": [
        {
            "input": {
                "workflow": "create_record",
                "kind": "length_word_boundary",
                "title": "A post with a really long title"
            },
            "expected_output": "workflow=create_record\nrecord_id=1\nrecord_count=1\ntitle=A post with a really long title\nslug=[a configured max length threshold]\nstored_slug=[a configured max length threshold]\nsecondary_slug=<null>\n"
        }
    ]
}
```

---

### Feature 6: Uniqueness and Collision Suffixes

**As a developer**, I want to avoid duplicate slugs when records share source text, so I can store multiple records with readable but unique identifiers.

**Expected Behavior / Usage:**

The input creates repeated records with the same source text. The output must include all generated slugs in creation order and the final persisted record count. The first record keeps the base slug, while later collisions receive deterministic suffixes according to the active uniqueness policy.

**Test Cases:** `rcb_tests/public_test_cases/feature6_uniqueness_and_suffixes.json`

```json
{
    "description": "When multiple records would otherwise receive the same slug, later records receive deterministic suffixes according to the active uniqueness policy.",
    "cases": [
        {
            "input": {
                "workflow": "create_repeated_records",
                "kind": "standard",
                "title": "A post title",
                "count": 3
            },
            "expected_output": "workflow=create_repeated_records\nrecord_count=3\nslugs=[a configured max length threshold]-title,[a configured max length threshold]-title-2,[a configured max length threshold]-title-3\n"
        }
    ]
}
```

---

### Feature 7: Reserved Values and Manual Slug Preservation

**As a developer**, I want to avoid reserved generated slugs and preserve explicit slug choices, so I can prevent generated identifiers from conflicting with reserved routes or user-provided identifiers.

**Expected Behavior / Usage:**

For reserved-value profiles, creating a record from reserved source text must print a suffixed slug instead of the reserved bare value. When the input supplies a non-empty slug explicitly, the saved record must keep that slug on creation and preserve it across later title-only updates; if a later input explicitly changes the slug, that new manual value is stored.

**Test Cases:** `rcb_tests/public_test_cases/feature7_reserved_and_manual_slugs.json`

```json
{
    "description": "Reserved generated values are avoided with a suffix, while explicitly supplied non-empty slug values are preserved across creation and later title updates.",
    "cases": [
        {
            "input": {
                "workflow": "create_record",
                "kind": "reserved_terms",
                "title": "Add"
            },
            "expected_output": "workflow=create_record\nrecord_id=1\nrecord_count=1\ntitle=Add\nslug=add-2\nstored_slug=add-2\nsecondary_slug=<null>\n"
        }
    ]
}
```

---

### Feature 8: Update-Time Regeneration

**As a developer**, I want to control whether slugs change after source updates, so I can keep existing URLs stable unless regeneration is explicitly required.

**Expected Behavior / Usage:**

The input creates a record and then updates its source title. The output must show the initial slug, updated title, final slug, and stored slug. Default update behavior preserves the existing slug on title changes, clearing the slug before update forces regeneration, and a regeneration-enabled profile updates the slug when the source value changes.

**Test Cases:** `rcb_tests/public_test_cases/feature8_update_regeneration.json`

```json
{
    "description": "Updating a record either preserves the current slug, regenerates it when the profile allows source updates, or regenerates it when the slug is manually cleared.",
    "cases": [
        {
            "input": {
                "workflow": "update_record",
                "kind": "standard",
                "title": "My First Post",
                "updated_title": "A New Title"
            },
            "expected_output": "workflow=update_record\ninitial_slug=my-first-post\nupdated_title=A New Title\nfinal_slug=my-first-post\nstored_slug=my-first-post\n"
        }
    ]
}
```

---

### Feature 9: Database Identifier in Slug Sources

**As a developer**, I want to include persistence-assigned identifiers in generated slugs when available, so I can combine readable text with stable database identity.

**Expected Behavior / Usage:**

The input creates one or more records using a profile that may include the database-assigned identifier in the source values. The output must show assigned identifiers and slugs. Profiles that generate after persistence include the identifier immediately and keep using it on later updates; profiles that generate before persistence cannot include an identifier until a later save when the identifier already exists.

**Test Cases:** `rcb_tests/public_test_cases/feature9_database_identifier_sources.json`

```json
{
    "description": "A slug source may include the database-assigned identifier only after the record has been saved; before-save generation cannot include an identifier that does not yet exist.",
    "cases": [
        {
            "input": {
                "workflow": "database_identifier_source",
                "kind": "saved_with_identifier_source",
                "first_title": "My First Post",
                "second_title": "My Second Post",
                "updated_first_title": "Still My First Post"
            },
            "expected_output": "workflow=database_identifier_source\nfirst_id=1\nfirst_initial_slug=[the auto-generated database primary key]\nsecond_id=2\nsecond_slug=my-second-post-2\nfirst_after_update_slug=still-[the auto-generated database primary key]\n"
        }
    ]
}
```

---

### Feature 10: Soft-Delete-Aware Uniqueness

**As a developer**, I want to decide whether deleted records reserve their slugs, so I can reuse identifiers safely according to the selected deletion policy.

**Expected Behavior / Usage:**

The input creates a record, soft-deletes it, then creates another record with the same source text. The output must show both slugs, that the first record was deleted, and the visible record count. One policy ignores deleted records so the slug can be reused; another includes deleted records so the replacement receives a collision suffix.

**Test Cases:** `rcb_tests/public_test_cases/feature10_soft_delete_uniqueness.json`

```json
{
    "description": "When a record is soft-deleted, uniqueness checks can either ignore that deleted record or continue to reserve its slug, depending on the selected deletion policy.",
    "cases": [
        {
            "input": {
                "workflow": "soft_delete_uniqueness",
                "kind": "soft_delete_excludes_deleted",
                "title": "A Post Title"
            },
            "expected_output": "workflow=soft_delete_uniqueness\nfirst_slug=[a configured max length threshold]-title\n[the boolean flag for soft-deleted records]\nsecond_slug=[a configured max length threshold]-title\nvisible_records=1\n"
        }
    ]
}
```

---

### Feature 11: Owner-Scoped Uniqueness

**As a developer**, I want to scope slug collisions by an associated owner, so I can allow different owners to reuse readable identifiers independently.

**Expected Behavior / Usage:**

The input creates owners and then records under those owners with repeated source text. The output must list slugs grouped by owner in creation order. Collisions are resolved within the same owner, while another owner can receive the base slug for the same source text.

**Test Cases:** `rcb_tests/public_test_cases/feature11_scoped_uniqueness.json`

```json
{
    "description": "Uniqueness can be scoped by an associated owner so identical source text collides within the same owner but not across different owners.",
    "cases": [
        {
            "input": {
                "workflow": "scoped_uniqueness",
                "authors": [
                    "Bob",
                    "Pam"
                ],
                "posts": [
                    {
                        "author": "Bob",
                        "title": "My first post"
                    },
                    {
                        "author": "Bob",
                        "title": "My first post"
                    },
                    {
                        "author": "Pam",
                        "title": "My first post"
                    },
                    {
                        "author": "Pam",
                        "title": "My first post"
                    }
                ]
            },
            "expected_output": "workflow=scoped_uniqueness\nauthors=Bob,Pam\nslugs_by_author=Bob:my-first-post,Bob:my-first-post-2,Pam:my-first-post,Pam:my-first-post-2\nrecord_count=4\n"
        }
    ]
}
```

---

### Feature 12: Lookup by Primary Slug

**As a developer**, I want to retrieve records through their slug value, so I can resolve user-facing URLs to stored records.

**Expected Behavior / Usage:**

The input seeds records and then selects a slug lookup mode and selector. Nullable lookup prints whether a matching record was found and includes record id and title when present. Strict lookup prints the found record for existing selectors and normalizes a missing selector to a language-neutral record-not-found error line without leaking runtime exception names.

**Test Cases:** `rcb_tests/public_test_cases/feature12_slug_lookup.json`

```json
{
    "description": "Records can be retrieved through their primary slug value; nullable lookup reports no match, while strict lookup normalizes a missing record to a record-not-found error.",
    "cases": [
        {
            "input": {
                "workflow": "lookup_by_slug",
                "lookup": "nullable",
                "titles": [
                    "A Post Title A",
                    "A Post Title B",
                    "A Post Title C"
                ],
                "slug": "[a configured max length threshold]-title-b"
            },
            "expected_output": "workflow=lookup_by_slug\nselector=[a configured max length threshold]-title-b\nfound=yes\nrecord_id=2\nrecord_title=A Post Title B\n"
        }
    ]
}
```

---

### Feature 13: Generation Without Saving

**As a developer**, I want to compute a slug for a target field without creating a new record, so I can preview identifiers or validate collisions before persistence.

**Expected Behavior / Usage:**

The input provides source text, a target slug field, optional existing records, and optional formatting settings. The output must print the number of existing records and the generated slug without saving a new record. Existing records are considered for uniqueness, custom separators affect formatting, and invalid target fields are normalized to a domain error category.

**Test Cases:** `rcb_tests/public_test_cases/feature13_static_generation.json`

```json
{
    "description": "A slug can be generated for a target field without saving a new record, while still accounting for existing stored records and normalizing invalid target fields to a domain error.",
    "cases": [
        {
            "input": {
                "workflow": "generate_without_saving",
                "target_field": "slug",
                "source_text": "My Test Post"
            },
            "expected_output": "workflow=generate_without_saving\nexisting_records=0\ntarget_field=slug\ngenerated_slug=my-test-post\n"
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
- follow the same ordering convention as the headers module
- refer to the legacy exception handler described in the authentication module
