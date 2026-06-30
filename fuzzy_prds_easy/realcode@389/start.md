## Product Requirement Document

# Media Service Utility Contracts - Configuration and Metadata Behavior

## Project Goal

Build a configuration and media metadata utility library that allows developers to parse application settings, preserve editable configuration text, represent media records, and resolve user directories without writing repetitive parsing, validation, serialization, and platform-path glue code.

---

## Background & Problem

Without this library/tool, developers are forced to hand-code raw text conversion, validate every setting separately, merge multiple configuration sources manually, maintain their own immutable metadata records, and implement platform directory discovery themselves. This leads to inconsistent error handling, repetitive boilerplate, and fragile metadata exchange.

With this library/tool, configuration and metadata behavior is expressed through small reusable contracts: raw inputs are converted into typed values, configuration files can be loaded and round-tripped, media records can be serialized and compared, and user directories can be resolved predictably.

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

### Feature 1: Configuration Value Conversion

**As a developer**, I want to define typed settings that convert raw text into useful values, so I can avoid hand-written parsing and validation for every setting.

**Expected Behavior / Usage:**

Raw setting values are provided with a neutral schema descriptor and an action. Deserialization trims and decodes strings, masks secrets only for display serialization, converts integers and booleans, splits lists on commas or newlines, maps log-level names to numeric levels, and enforces network port ranges. Successful output is the converted value as JSON or raw text where the serialized form is bytes. Invalid input is reported as a neutral error category instead of a host-language exception.

**Test Cases:** `rcb_tests/public_test_cases/feature1_config_value_conversion.json`

```json
{
    "cases": [
        {
            "expected_output": "\"foo\"\n",
            "input": {
                "operation": "config_value",
                "schema": {
                    "type": "string"
                },
                "value": " foo "
            }
        },
        {
            "expected_output": "[a specific literal string consisting of asterisks — verify with the team]\n",
            "input": {
                "action": "serialize",
                "bytes": false,
                "display": true,
                "operation": "config_value",
                "schema": {
                    "type": "secret"
                },
                "value": "s3cret"
            }
        },
        {
            "expected_output": "true\n",
            "input": {
                "bytes": false,
                "operation": "config_value",
                "schema": {
                    "type": "boolean"
                },
                "value": "YES"
            }
        },
        {
            "expected_output": "[\"foo\", \"bar\", \"baz\"]\n",
            "input": {
                "operation": "config_value",
                "schema": {
                    "type": "list"
                },
                "value": "foo, bar ,baz "
            }
        },
        {
            "expected_output": "65535\n",
            "input": {
                "bytes": false,
                "operation": "config_value",
                "schema": {
                    "type": "port"
                },
                "value": "65535"
            }
        },
        {
            "expected_output": "error=invalid_value\n",
            "input": {
                "bytes": false,
                "operation": "config_value",
                "schema": {
                    "type": "port"
                },
                "value": "65536"
            }
        }
    ],
    "description": "Typed configuration values are converted, serialized, validated, and report neutral errors for invalid input."
}
```

---

### Feature 2: Configuration Source Loading

**As a developer**, I want to merge settings from defaults, files, directories, and command-line overrides, so I can produce one effective configuration map.

**Expected Behavior / Usage:**

The input describes zero or more default configuration snippets, file-like configuration sources, directory-like sources, and override triples. The output is a JSON object keyed by section name, then setting name. Missing files are ignored. Directory sources load only entries with a configuration-file extension. Overrides are applied as explicit section/key/value triples.

**Test Cases:** `rcb_tests/public_test_cases/feature2_config_sources.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"foo\": {\"bar\": \"baz\"}}\n",
            "input": {
                "defaults": [
                    "[foo]\nbar = baz"
                ],
                "operation": "config_load"
            }
        },
        {
            "expected_output": "{\"foo\": {\"bar\": \"baz\"}, \"foo2\": {\"bar\": \"baz\"}}\n",
            "input": {
                "operation": "config_load",
                "overrides": [
                    [
                        "foo",
                        "bar",
                        "baz"
                    ],
                    [
                        "foo2",
                        "bar",
                        "baz"
                    ]
                ]
            }
        },
        {
            "expected_output": "{\"foo\": {\"bar\": \"baz\"}, \"foo2\": {\"bar\": \"baz\"}}\n",
            "input": {
                "files": [
                    {
                        "entries": {
                            "file1.conf": "[foo]\nbar = baz",
                            "file2.conf": "[foo2]\nbar = baz",
                            "ignored.disabled": "[bad]\nkey = value"
                        },
                        "kind": "directory"
                    }
                ],
                "operation": "config_load"
            }
        }
    ],
    "description": "Configuration data is assembled from defaults, files, directories, and overrides with later sources supplying keys."
}
```

---

### Feature 3: Configuration Comment Preservation

**As a developer**, I want to preserve comments and section suffix text while parsing configuration files, so I can round-trip user-edited files without discarding context.

**Expected Behavior / Usage:**

The input contains a text block and an action. Normalization converts comments, blank lines, section suffix text, and semicolon inline comments into placeholder key/value lines under a synthetic comments section so a generic INI parser can keep them. Denormalization converts those placeholders back into the original user-facing text. Hash characters inside values are not treated as inline comments.

**Test Cases:** `rcb_tests/public_test_cases/feature3_config_comment_roundtrip.json`

```json
{
    "cases": [
        {
            "expected_output": "[two internal placeholder magic strings — check the constants file]\n[section]\nfoo = bar\n[two internal placeholder magic strings — check the constants file] = baz\n",
            "input": {
                "action": "preprocess",
                "operation": "config_comments",
                "text": "[section]\nfoo = bar ; baz"
            }
        },
        {
            "expected_output": "[section]\nfoo = bar ; baz\n",
            "input": {
                "action": "postprocess",
                "operation": "config_comments",
                "text": "[two internal placeholder magic strings — check the constants file]\n[section]\nfoo = bar\n[two internal placeholder magic strings — check the constants file] = baz"
            }
        }
    ],
    "description": "Configuration text preserves initial comments, section suffixes, blank lines, and semicolon inline comments across a reversible normalization."
}
```

---

### Feature 4: Media Entity Serialization

**As a developer**, I want to represent library objects as immutable records that can be serialized, so I can exchange nested media metadata through JSON-compatible data.

**Expected Behavior / Usage:**

The input describes a media entity with fields and optional nested entities. The output is a JSON-compatible record containing an entity type marker plus only the fields that carry values. Nested related entities are recursively serialized. JSON encoding and decoding must preserve equality with the original entity.

**Test Cases:** `rcb_tests/public_test_cases/feature4_media_entity_serialization.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"__model__\": \"Artist\", \"name\": \"Name\", \"uri\": \"artist:1\"}\n",
            "input": {
                "object": {
                    "entity": "artist",
                    "fields": {
                        "name": "Name",
                        "uri": "artist:1"
                    }
                },
                "operation": "model_serialize"
            }
        },
        {
            "expected_output": "{\"__model__\": \"Track\", \"album\": {\"__model__\": \"Album\", \"artists\": [{\"__model__\": \"Artist\", \"name\": \"Name\", \"uri\": \"artist:1\"}], \"name\": \"Album\", \"uri\": \"album:1\"}, \"artists\": [{\"__model__\": \"Artist\", \"name\": \"Name\", \"uri\": \"artist:1\"}], \"name\": \"Song\", \"uri\": \"track:1\"}\n",
            "input": {
                "object": {
                    "entity": "track",
                    "fields": {
                        "album": {
                            "entity": "album",
                            "fields": {
                                "artists": [
                                    {
                                        "entity": "artist",
                                        "fields": {
                                            "name": "Name",
                                            "uri": "artist:1"
                                        }
                                    }
                                ],
                                "name": "Album",
                                "uri": "album:1"
                            }
                        },
                        "artists": [
                            {
                                "entity": "artist",
                                "fields": {
                                    "name": "Name",
                                    "uri": "artist:1"
                                }
                            }
                        ],
                        "name": "Song",
                        "uri": "track:1"
                    }
                },
                "operation": "model_serialize"
            }
        },
        {
            "expected_output": "{\"encoded\": {\"__model__\": \"Track\", \"album\": {\"__model__\": \"Album\", \"artists\": [{\"__model__\": \"Artist\", \"name\": \"Name\", \"uri\": \"artist:1\"}], \"name\": \"Album\", \"uri\": \"album:1\"}, \"artists\": [{\"__model__\": \"Artist\", \"name\": \"Name\", \"uri\": \"artist:1\"}], \"name\": \"Song\", \"uri\": \"track:1\"}, \"roundtrip_equal\": true}\n",
            "input": {
                "object": {
                    "entity": "track",
                    "fields": {
                        "album": {
                            "entity": "album",
                            "fields": {
                                "artists": [
                                    {
                                        "entity": "artist",
                                        "fields": {
                                            "name": "Name",
                                            "uri": "artist:1"
                                        }
                                    }
                                ],
                                "name": "Album",
                                "uri": "album:1"
                            }
                        },
                        "artists": [
                            {
                                "entity": "artist",
                                "fields": {
                                    "name": "Name",
                                    "uri": "artist:1"
                                }
                            }
                        ],
                        "name": "Song",
                        "uri": "track:1"
                    }
                },
                "operation": "model_json_roundtrip"
            }
        }
    ],
    "description": "Media entities serialize to JSON-compatible records that include a model marker and nested related entities."
}
```

---

### Feature 5: Media Entity Update and Comparison

**As a developer**, I want to create modified copies of immutable media records, so I can update metadata without mutating existing values.

**Expected Behavior / Usage:**

The input describes an entity and either replacements, a comparison target, or a playlist length query. Replacing fields returns a new serialized record with unchanged fields retained; replacing a field with null removes that field when null is its default. Entity comparison is by content rather than identity, and unordered artist collections compare equal regardless of order. Playlist length is derived from the number of contained tracks. Unknown replacement fields return a neutral invalid-type error.

**Test Cases:** `rcb_tests/public_test_cases/feature5_media_entity_update_and_compare.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"__model__\": \"Track\", \"name\": \"New\", \"uri\": \"track:1\"}\n",
            "input": {
                "object": {
                    "entity": "track",
                    "fields": {
                        "name": "Old",
                        "uri": "track:1"
                    }
                },
                "operation": "model_replace",
                "replace": {
                    "name": "New"
                }
            }
        },
        {
            "expected_output": "{\"equal\": true}\n",
            "input": {
                "left": {
                    "entity": "album",
                    "fields": {
                        "artists": [
                            {
                                "entity": "artist",
                                "fields": {
                                    "name": "A"
                                }
                            },
                            {
                                "entity": "artist",
                                "fields": {
                                    "name": "B"
                                }
                            }
                        ]
                    }
                },
                "operation": "model_compare",
                "right": {
                    "entity": "album",
                    "fields": {
                        "artists": [
                            {
                                "entity": "artist",
                                "fields": {
                                    "name": "B"
                                }
                            },
                            {
                                "entity": "artist",
                                "fields": {
                                    "name": "A"
                                }
                            }
                        ]
                    }
                }
            }
        },
        {
            "expected_output": "length=3\n",
            "input": {
                "object": {
                    "entity": "playlist",
                    "fields": {
                        "tracks": [
                            {
                                "entity": "track",
                                "fields": {}
                            },
                            {
                                "entity": "track",
                                "fields": {}
                            },
                            {
                                "entity": "track",
                                "fields": {}
                            }
                        ]
                    }
                },
                "operation": "playlist_length"
            }
        }
    ],
    "description": "Media entities are immutable value records that can produce updated copies, compare by content, and expose derived playlist length."
}
```

---

### Feature 6: References and Queue Items

**As a developer**, I want to create lightweight typed references and track-list queue entries, so I can carry navigable identifiers without full metadata.

**Expected Behavior / Usage:**

A reference input contains a reference kind, URI, and display name; the output is a serialized reference record with the corresponding type. A queue item input contains a stable list id and a track; it serializes as a pair-like record and can also be unpacked into the id plus serialized track.

**Test Cases:** `rcb_tests/public_test_cases/feature6_references_and_queue_items.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"__model__\": \"Ref\", \"name\": \"Foo\", \"type\": \"album\", \"uri\": \"album:foo\"}\n",
            "input": {
                "kind": "album",
                "name": "Foo",
                "operation": "ref_factory",
                "uri": "album:foo"
            }
        },
        {
            "expected_output": "{\"tlid\": 123, \"track\": {\"__model__\": \"Track\", \"uri\": \"track:foo\"}}\n",
            "input": {
                "object": {
                    "entity": "queue_item",
                    "fields": {
                        "tlid": 123,
                        "track": {
                            "entity": "track",
                            "fields": {
                                "uri": "track:foo"
                            }
                        }
                    },
                    "positional": true
                },
                "operation": "tl_track_iter"
            }
        }
    ],
    "description": "Lightweight references carry URI, display name, and type; queue entries pair a stable list id with a track and can be unpacked."
}
```

---

### Feature 7: Locale-Aware Error Text Decoding

**As a developer**, I want to decode byte-oriented system error text into readable text, so I can show localized operating-system messages correctly.

**Expected Behavior / Usage:**

The input is either a raw byte sequence encoded as hexadecimal, a structured I/O error with a numeric code and byte message, or an already-decoded string. Byte values are decoded through the active locale and output as readable text. Already-decoded text is returned unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature7_locale_error_decoding.json`

```json
{
    "cases": [
        {
            "expected_output": "[a specific Python exception message format — request precise output from backend]\n",
            "input": {
                "encoding": "hex",
                "operation": "locale_decode",
                "value": "5b4572726e6f2039385d20416472657373652064c3a96ac3a0207574696c6973c3a965"
            }
        },
        {
            "expected_output": "abc\n",
            "input": {
                "operation": "locale_decode",
                "value": "abc"
            }
        }
    ],
    "description": "Byte-oriented error text is decoded with the active locale while text strings are returned unchanged."
}
```

---

### Feature 8: User Directory Resolution

**As a developer**, I want to resolve standard user data, config, cache, and media directories, so I can honor environment overrides and user directory files.

**Expected Behavior / Usage:**

The input supplies an environment map, optional user directory file content, and requested keys. The output is a JSON object containing only the requested directories that resolve. Environment variables override defaults for cache, config, and data directories. A user directory file may define media directories using a home-directory placeholder; absent entries are omitted.

**Test Cases:** `rcb_tests/public_test_cases/feature8_xdg_directory_resolution.json`

```json
{
    "cases": [
        {
            "expected_output": "{\"XDG_CACHE_DIR\": \"/root/.cache\", \"XDG_CONFIG_DIR\": \"/root/.config\", \"XDG_DATA_DIR\": \"/root/.local/share\"}\n",
            "input": {
                "env": {},
                "keys": [
                    "XDG_CACHE_DIR",
                    "XDG_CONFIG_DIR",
                    "XDG_DATA_DIR"
                ],
                "operation": "xdg_dirs"
            }
        },
        {
            "expected_output": "{\"XDG_CACHE_DIR\": \"/foo/bar\"}\n",
            "input": {
                "env": {
                    "XDG_CACHE_HOME": "/foo/bar"
                },
                "keys": [
                    "XDG_CACHE_DIR"
                ],
                "operation": "xdg_dirs"
            }
        },
        {
            "expected_output": "{\"XDG_MUSIC_DIR\": \"/root/Music2\"}\n",
            "input": {
                "env": {
                    "XDG_CONFIG_HOME": "/tmp/rcb_xdg"
                },
                "keys": [
                    "XDG_MUSIC_DIR",
                    "XDG_DOWNLOAD_DIR"
                ],
                "operation": "xdg_dirs",
                "user_dirs_content": "# Some comments\nXDG_MUSIC_DIR=\"$HOME/Music2\"\n"
            }
        }
    ],
    "description": "Standard user directories resolve from environment variables, defaults, and optional user directory configuration files."
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_config_value_conversion.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_config_value_conversion@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same integer handling as the battery_report serializer
- use the standard extension logic applied to XDG_* environment variables
