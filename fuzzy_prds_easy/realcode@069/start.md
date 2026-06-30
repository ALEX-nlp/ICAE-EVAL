## Product Requirement Document

# Repository Discovery and Publishing Assistant - Select and Share Repository Highlights

## Project Goal

Build a repository discovery and publishing assistant that allows developers to find candidate repositories, transform their metadata into publishable content, and send that content to document and social destinations without repeatedly hand-writing query construction, cache checks, formatting, duplicate detection, and dry-run publishing logic.

---

## Background & Problem

Without this library/tool, developers are forced to manually assemble repository search filters, remember which repositories were already selected, normalize tags, build social post text, inspect existing document content, and coordinate multiple publishing destinations. This leads to repetitive code, fragile publishing workflows, accidental duplicate entries, and inconsistent output formatting.

With this library/tool, discovery configuration, repository metadata, cache state, and destination rules are converted into deterministic publishable outputs through a small execution adapter and a core system that remains independent of standard input/output concerns.

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

### Feature 1: Hashtag List Normalization

**As a developer**, I want to normalize an optional comma-separated tag list, so I can use consistent hash-prefixed labels in generated publishing metadata.

**Expected Behavior / Usage:**

The input is an object with a tag-list string. The output is two lines: a comma-joined normalized tag list and the number of generated tags. Empty tag input produces an empty tag line and a zero count. Each non-empty item is trimmed and prefixed with `#`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_hashtag_list.json`

```json
{
    "description": "Converts an optional comma-separated tag list into normalized hash-prefixed tags while trimming surrounding spaces.",
    "cases": [
        {
            "input": {
                "hashtags": "a,b,c "
            },
            "expected_output": "hashtags=#a,#b,#c\ncount=3\n"
        }
    ]
}
```

---
### Feature 2: Cache Operation Semantics

**As a developer**, I want to read and mutate a key-value cache through a simple operation list, so I can verify whether repository identifiers and other values are remembered between operations.

**Expected Behavior / Usage:**

The input is an ordered list of cache operations. Each operation names an action and key, and set operations also include a value. The output contains one line per operation, preserving input order. Missing reads are reported as `missing`, successful writes as `stored`, successful deletes as `deleted`, and successful reads as the stored value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_cache_operations.json`

```json
{
    "description": "Stores, retrieves, and deletes string values through the cache abstraction, reporting observable cache state after each requested operation.",
    "cases": [
        {
            "input": {
                "operations": [
                    {
                        "action": "set",
                        "key": "key",
                        "value": "v"
                    },
                    {
                        "action": "get",
                        "key": "key"
                    }
                ]
            },
            "expected_output": "set:key=stored\nget:key=v\n"
        }
    ]
}
```

---
### Feature 3.1: Repository Search Query Construction

**As a developer**, I want to build repository search queries from discovery filters, so I can search with the expected topic and language constraints.

**Expected Behavior / Usage:**

The input contains a seed character plus optional topic and language filters. The output is a single `query=` line. When both topic and language are present, both filters appear in that order. When only one filter is present, only that filter appears. With no filters, the query still contains an empty language filter. A non-blank seed is prepended to the filter expression.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_search_query.json`

```json
{
    "description": "Builds a repository search query from a seed character and optional topic and language filters.",
    "cases": [
        {
            "input": {
                "random_character": "a",
                "config": {
                    "topic": "x",
                    "language": "g"
                }
            },
            "expected_output": "query=a+topic:x+language:g\n"
        },
        {
            "input": {
                "random_character": "a",
                "config": {
                    "language": "g"
                }
            },
            "expected_output": "query=a+language:g\n"
        }
    ]
}
```

---
### Feature 3.2: Repository Cache Admission

**As a developer**, I want to decide whether a discovered repository is new enough to use, so I can avoid repeatedly selecting the same repository.

**Expected Behavior / Usage:**

The input describes a repository identifier and the simulated cache read/write outcome. The output is `admitted=true` only when the identifier is absent from cache and the attempt to record it succeeds. Existing identifiers, cache read errors, and cache write errors all produce `admitted=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_cache_admission.json`

```json
{
    "description": "Determines whether a repository identifier is newly admissible by checking cache presence and whether a missing identifier can be recorded.",
    "cases": [
        {
            "input": {
                "config": {
                    "topic": "x"
                },
                "repository": {
                    "id": 10
                },
                "cache_get": "missing"
            },
            "expected_output": "admitted=true\n"
        },
        {
            "input": {
                "config": {
                    "topic": "x"
                },
                "repository": {
                    "id": 10
                },
                "cache_get": "present"
            },
            "expected_output": "admitted=false\n"
        }
    ]
}
```

---
### Feature 3.3: Cache Expiration Window

**As a developer**, I want to compute the cache retention window from scheduling settings, so I can keep recently used repository identifiers for the intended number of minutes.

**Expected Behavior / Usage:**

The input contains a cache-size value and a periodicity value. The output is the computed expiration in minutes. The expiration is the product of those two values, except any negative result is clamped to zero minutes.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_cache_expiration.json`

```json
{
    "description": "Computes the cache expiration window as cache size multiplied by periodicity, clamping negative products to zero minutes.",
    "cases": [
        {
            "input": {
                "config": {
                    "cache_size": 10,
                    "periodicity": 2
                }
            },
            "expected_output": "expiration_minutes=20\n"
        },
        {
            "input": {
                "config": {
                    "cache_size": -10,
                    "periodicity": 2
                }
            },
            "expected_output": "expiration_minutes=0\n"
        }
    ]
}
```

---
### Feature 3.4: Owner Social Username Lookup

**As a developer**, I want to extract a social username from repository owner metadata, so I can credit the repository author when that information is available.

**Expected Behavior / Usage:**

The input describes whether an owner exists, whether the owner has a lookup name, and whether the profile lookup returns a social username. The output is one `twitter_username=` line. Missing owners, missing lookup names, lookup failures, and profiles without a username all produce an empty value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_owner_profile.json`

```json
{
    "description": "Extracts a social username from a repository owner profile when the owner has a login and the profile lookup returns a username.",
    "cases": [
        {
            "input": {
                "owner_lookup": "no_owner"
            },
            "expected_output": "twitter_username=\n"
        },
        {
            "input": {
                "owner_lookup": "t2",
                "owner_twitter": "twitterusername"
            },
            "expected_output": "twitter_username=twitterusername\n"
        }
    ]
}
```

---
### Feature 3.5: Publishable Repository Summary

**As a developer**, I want to convert repository metadata into a publishable content summary, so I can send downstream publishers a consistent title, subtitle, URL, and auxiliary metadata.

**Expected Behavior / Usage:**

The input combines repository metadata with discovery configuration. The output contains `title`, `subtitle`, `url`, and a pipe-separated `extra_data` line. Auxiliary data is ordered: requested language metadata line, star count, author handle, then hashtags. Explicit configured hashtags override derived hashtags; otherwise the hashtag is derived from configured topic, configured language, or repository language in that priority order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_content_summary.json`

```json
{
    "description": "Converts repository metadata and configuration into publishable content fields plus ordered auxiliary lines such as language, stars, author, and hashtags.",
    "cases": [
        {
            "input": {
                "config": {},
                "repository": {
                    "language": "g",
                    "url": "url"
                }
            },
            "expected_output": "title=\nsubtitle=\nurl=url\nextra_data=#g \n"
        },
        {
            "input": {
                "config": {
                    "include_language_line": true
                },
                "repository": {
                    "name": "repo",
                    "description": "desc",
                    "language": "g",
                    "url": "url",
                    "stars": 1,
                    "owner_login": "t2"
                },
                "owner_twitter": "twitterusername"
            },
            "expected_output": "title=repo\nsubtitle=desc\nurl=url\nextra_data=Lang: g|⭐️ 1|Author: @twitterusername|#g \n"
        }
    ]
}
```

---
### Feature 3.6: Repository Selection Outcome

**As a developer**, I want to select a usable repository from search results, so I can publish only when search returns an available, non-archived, cache-admissible repository.

**Expected Behavior / Usage:**

The input describes search behavior, available pages, and candidate repositories. The output is a normalized repository identifier when a repository can be selected. Search failures and empty search results produce `error=repository_unavailable`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_6_repository_selection.json`

```json
{
    "description": "Selects a non-archived repository from search results only when search succeeds, there is at least one page of results, and cache admission succeeds.",
    "cases": [
        {
            "input": {
                "last_page": 1,
                "total": 1000,
                "repositories": [
                    {
                        "id": 1,
                        "archived": false
                    },
                    {
                        "id": 2,
                        "archived": true
                    }
                ]
            },
            "expected_output": "repository_id=1\n"
        }
    ]
}
```

---
### Feature 4.1: Base64 Document Decoding

**As a developer**, I want to decode stored document text, so I can inspect existing document content before deciding whether to append a repository link.

**Expected Behavior / Usage:**

The input contains encoded text. The output is `decoded=<text>` for valid base64 input. Invalid encoded input produces the language-neutral error line `error=invalid_base64`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_base64_decoding.json`

```json
{
    "description": "Decodes valid base64 text into plain text and reports invalid encoded input with a language-neutral error category.",
    "cases": [
        {
            "input": {
                "encoded_text": "c29tZXRleHQ="
            },
            "expected_output": "decoded=sometext\n"
        }
    ]
}
```

---
### Feature 4.2: Repository Link Publishing to a Document

**As a developer**, I want to append a repository link to existing document content, so I can maintain a curated document without adding duplicates or corrupting unreadable content.

**Expected Behavior / Usage:**

The input contains safe-mode settings, optional content to publish, and simulated existing-document/update outcomes. A publishable item requires a title and URL; subtitle is optional. In safe mode, valid content reports `published=true` without reading or updating a document. Outside safe mode, existing content must be readable, base64-decodable, and not already contain the repository title; then the update must succeed. Outputs always include `published=<bool>` and, on failure, one normalized error category.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_readme_publishing.json`

```json
{
    "description": "Adds a repository link to existing encoded document content unless required content is missing, the existing content cannot be read or decoded, the link already exists, or the update fails.",
    "cases": [
        {
            "input": {
                "safe_mode": true,
                "content": {
                    "title": "sometext",
                    "url": "url"
                }
            },
            "expected_output": "published=true\n"
        },
        {
            "input": {
                "content": {
                    "title": "sometext",
                    "subtitle": "sub",
                    "url": "url"
                },
                "existing_file_content": "c29tZXRleHQ="
            },
            "expected_output": "published=false\nerror=duplicate_content\n"
        },
        {
            "input": {
                "content": {
                    "title": "sometext",
                    "subtitle": "sub",
                    "url": "url"
                },
                "existing_file_content": "sometext"
            },
            "expected_output": "published=true\n"
        }
    ]
}
```

---
### Feature 5.1: Tweet Body Formatting

**As a developer**, I want to format publishable content as a social post, so I can share repository title, description, auxiliary lines, and URL within the post length limit.

**Expected Behavior / Usage:**

The input contains title, subtitle, ordered auxiliary lines, and URL. The output contains the generated post text with line breaks rendered as `\n`, plus its character length. If the generated text would exceed the supported post length, the subtitle is truncated and suffixed with ` ...` so the final text fits.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_tweet_formatting.json`

```json
{
    "description": "Formats publishable content as a tweet body, preserving ordered auxiliary lines and truncating an overlong subtitle to fit the tweet-length boundary.",
    "cases": [
        {
            "input": {
                "title": "Lorem Ipsum",
                "subtitle": "t",
                "extra_data": [
                    "50k",
                    "Author: @unknown"
                ],
                "url": "https://loremipsum.io/generator/?n=3&t=s",
                "safe_mode": true
            },
            "expected_output": "tweet=Lorem Ipsum: t\\n50k\\nAuthor: @unknown\\nhttps://loremipsum.io/generator/?n=3&t=s\nlength=76\n"
        },
        {
            "input": {
                "title": "Lorem Ipsum",
                "subtitle": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Vitae sapien pellentesque habitant morbi tristique senectus et netus et. Nunc sed velit dignissim sodales.",
                "extra_data": [
                    "50k",
                    "Author: @unknown"
                ],
                "url": "https://loremipsum.io/generator/?n=3&t=s",
                "safe_mode": true
            },
            "expected_output": "tweet=Lorem Ipsum: Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Vitae sapien pellentesque habitant morbi tristique senectus et netus et. Nunc ...\\n50k\\nAuthor: @unknown\\nhttps://loremipsum.io/generator/?n=3&t=s\nlength=280\n"
        }
    ]
}
```

---
### Feature 5.2: Safe-Mode Social Publishing

**As a developer**, I want to exercise social publishing without contacting an external network, so I can confirm that complete content can be accepted during dry-run execution.

**Expected Behavior / Usage:**

The input contains complete post content and safe-mode enabled. The output reports `published=true` when formatting succeeds and no external publication is attempted.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_safe_mode_tweet_publish.json`

```json
{
    "description": "Reports a successful publication result in safe mode after formatting complete tweet content without contacting an external social network.",
    "cases": [
        {
            "input": {
                "title": "ti",
                "subtitle": "s",
                "url": "u",
                "extra_data": [],
                "safe_mode": true
            },
            "expected_output": "published=true\n"
        }
    ]
}
```

---
### Feature 6: Provider-to-Publisher Orchestration

**As a developer**, I want to run the full provider-to-publishers flow, so I can retrieve one content item and pass it to every configured destination.

**Expected Behavior / Usage:**

The input describes whether provider retrieval fails and how many publishers are configured. If provider retrieval fails, the output reports `result=provider_error` and no publishers are called. Otherwise the output reports `result=completed` and the number of publisher calls equals the configured publisher count.

**Test Cases:** `rcb_tests/public_test_cases/feature6_service_orchestration.json`

```json
{
    "description": "Retrieves one content item from a provider and sends it to every configured publisher, stopping before publishers only when provider retrieval fails.",
    "cases": [
        {
            "input": {
                "provider_error": true,
                "publisher_count": 1
            },
            "expected_output": "result=provider_error\npublish_calls=0\n"
        },
        {
            "input": {
                "provider_error": false,
                "publisher_count": 1
            },
            "expected_output": "result=completed\npublish_calls=1\n"
        }
    ]
}
```

---
## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_hashtag_list.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_hashtag_list@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the strict reordering protocol found in the cache_ops劳工.py file
- apply the silent publishing flag from the config.yaml safe_mode section
