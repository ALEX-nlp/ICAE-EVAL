## Product Requirement Document

# Convention-Based Code Loader - Lazy Path-to-Constant Loading

## Project Goal

Build a convention-based code loader that allows developers to organize source files in directories and access constants by name without writing manual require statements or registration tables.

---

## Background & Problem

Without this library/tool, developers are forced to keep file-loading order, namespace setup, duplicate path handling, and reload cleanup in hand-written boot code. This leads to repetitive boilerplate, load-order bugs, stale constants in development, and inconsistent behavior between lazy and eager execution paths.

With this library/tool, a developer declares source roots and the loader infers names from paths, loads files only when needed or eagerly on request, supports reload/unload cycles, and reports loader contract failures in a predictable way.

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

### Feature 1: Name Inference

**As a developer, I want file-like names to be converted into loadable constant names**, so I can organize code by predictable paths without writing repetitive registration code.

**Expected Behavior / Usage:**

*1.1 Default Basename Mapping — Convert a single file basename or underscore-separated basename into a constant-style name by capitalizing each underscore-delimited segment and joining the segments.*

Convert a single file basename or underscore-separated basename into a constant-style name by capitalizing each underscore-delimited segment and joining the segments. Numeric characters stay in their original segment. Acronyms are not guessed unless explicitly configured.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_default_name_mapping.json`

```json
{
    "description": "Map underscore-separated file basenames to constant names using simple capitalization for each segment.",
    "cases": [
        {
            "input": {
                "operation": "inflect_basename",
                "basenames": [
                    "user",
                    "users_controller",
                    "point_3d_value",
                    "html_parser"
                ]
            },
            "expected_output": "basename=user\nconstant=User\nbasename=users_controller\nconstant=UsersController\nbasename=point_3d_value\nconstant=Point3dValue\nbasename=html_parser\nconstant=HtmlParser\n"
        }
    ]
}
```

*1.2 Custom Name Overrides — Accept explicit basename mappings that take precedence over the default conversion.*

Accept explicit basename mappings that take precedence over the default conversion. Basenames not present in the override map continue to use default conversion.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_custom_name_overrides.json`

```json
{
    "description": "Apply explicit basename-to-constant-name mappings while preserving default mapping for basenames without an override.",
    "cases": [
        {
            "input": {
                "operation": "inflect_with_overrides",
                "overrides": {
                    "html_parser": "HTMLParser",
                    "csv_controller": "CSVController",
                    "mysql_adapter": "MySQLAdapter"
                },
                "basenames": [
                    "html_parser",
                    "csv_controller",
                    "mysql_adapter",
                    "users_controller"
                ]
            },
            "expected_output": "basename=html_parser\nconstant=HTMLParser\nbasename=csv_controller\nconstant=CSVController\nbasename=mysql_adapter\nconstant=MySQLAdapter\nbasename=users_controller\nconstant=UsersController\n"
        }
    ]
}
```

*1.3 Package Version File Mapping — When resolving files for a packaged library, the direct version file below the package namespace maps to an all-caps version constant, while nested version files and ordinary files use the normal basename mapping.*

When resolving files for a packaged library, the direct version file below the package namespace maps to an all-caps version constant, while nested version files and ordinary files use the normal basename mapping.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_package_version_name_mapping.json`

```json
{
    "description": "For a library root file, map the direct version file under the library namespace to an all-caps version constant and map other version files normally.",
    "cases": [
        {
            "input": {
                "operation": "gem_file_mapping",
                "paths": [
                    "main_version_file",
                    "nested_version_file",
                    "ordinary_file"
                ]
            },
            "expected_output": "path=main_version_file\nconstant=VERSION\npath=nested_version_file\nconstant=Version\npath=ordinary_file\nconstant=Widget\n"
        }
    ]
}
```

---

### Feature 2: Root Scanning and Top-Level Lazy Loading

**As a developer, I want the loader to scan configured source roots and load top-level entries on demand**, so startup can remain lightweight while constants remain available by name.

**Expected Behavior / Usage:**

*2.1 Top-Level Lazy Loading — Given one or more source roots, source files whose basenames infer top-level constants are registered.*

Given one or more source roots, source files whose basenames infer top-level constants are registered. The file is evaluated when the constant is first accessed, and dependencies between managed constants can be resolved during that load.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_lazy_top_level_loading.json`

```json
{
    "description": "Load top-level constants from matching source files on first access across one or more configured root directories.",
    "cases": [
        {
            "input": {
                "operation": "lazy_constant_loading",
                "roots": [
                    "app/models",
                    "app/controllers"
                ],
                "files": {
                    "app/models/user.rb": "class User; end",
                    "app/controllers/users_controller.rb": "class UsersController; User; end"
                },
                "access": [
                    "User",
                    "UsersController"
                ]
            },
            "expected_output": "constant=User\nvalue=class\nconstant=UsersController\nvalue=class\n"
        }
    ]
}
```

*2.2 Non-Code Entry Ignoring — Entries that are not loadable source files, backup files, editor artifacts, and hidden tool directories are ignored during root scanning and do not create available constants.*

Entries that are not loadable source files, backup files, editor artifacts, and hidden tool directories are ignored during root scanning and do not create available constants.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_non_code_entries_ignored.json`

```json
{
    "description": "Ignore files that are not loadable source files and ignore hidden directories while scanning roots.",
    "cases": [
        {
            "input": {
                "operation": "ignored_paths",
                "roots": [
                    "."
                ],
                "files": {
                    "x.txt": "",
                    "x.yaml": "",
                    "x.rb~": "",
                    "#x.rb#": "",
                    ".idea/workspace.xml": ""
                },
                "access": [
                    "X"
                ]
            },
            "expected_output": "constant=X\navailable=no\n"
        }
    ]
}
```

---

### Feature 3: Directory Namespaces

**As a developer, I want directories to act as namespaces**, so nested source files can be loaded without manually defining every intermediate namespace.

**Expected Behavior / Usage:**

*3.1 Implicit Namespace Loading — If a directory corresponds to a missing namespace, the loader creates that namespace on first access and then makes source files under the directory available as nested constants.*

If a directory corresponds to a missing namespace, the loader creates that namespace on first access and then makes source files under the directory available as nested constants. This works through several directory levels.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_implicit_namespace_loading.json`

```json
{
    "description": "Create missing namespace modules from directories and then load constants stored below those directories.",
    "cases": [
        {
            "input": {
                "operation": "implicit_namespace_loading",
                "roots": [
                    "."
                ],
                "files": {
                    "admin/x.rb": "Admin::X = true"
                },
                "access": [
                    "Admin",
                    "Admin::X"
                ]
            },
            "expected_output": "constant=Admin\nvalue=module\nconstant=Admin::X\nvalue=true\n"
        }
    ]
}
```

*3.2 Shared Namespaces Across Roots — When several roots contain subdirectories for the same namespace, the namespace is shared and nested constants from every matching root remain available.*

When several roots contain subdirectories for the same namespace, the namespace is shared and nested constants from every matching root remain available.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_shared_namespace_across_roots.json`

```json
{
    "description": "Combine matching subdirectories from multiple roots into one namespace so constants from each root remain available.",
    "cases": [
        {
            "input": {
                "operation": "implicit_namespace_loading",
                "roots": [
                    "app/models",
                    "app/controllers"
                ],
                "files": {
                    "app/models/admin/hotel.rb": "class Admin::Hotel; end",
                    "app/controllers/admin/hotels_controller.rb": "class Admin::HotelsController; end"
                },
                "access": [
                    "Admin::Hotel",
                    "Admin::HotelsController"
                ]
            },
            "expected_output": "constant=Admin::Hotel\nvalue=class\nconstant=Admin::HotelsController\nvalue=class\n"
        }
    ]
}
```

---

### Feature 4: Explicit Namespace Files

**As a developer, I want namespace files and namespace directories to cooperate**, so a namespace can define behavior in its own file and still expose nested files.

**Expected Behavior / Usage:**

*4.1 Explicit Namespace Loading — If a namespace has both a source file and a matching directory, accessing the namespace loads the namespace file, and nested constants below the matching directory remain available afterwards.*

If a namespace has both a source file and a matching directory, accessing the namespace loads the namespace file, and nested constants below the matching directory remain available afterwards. The behavior must not depend on a user-visible name override inside the namespace object.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_explicit_namespace_loading.json`

```json
{
    "description": "When a namespace has its own source file and a matching directory, load the namespace file and keep its nested constants available.",
    "cases": [
        {
            "input": {
                "operation": "explicit_namespace_loading",
                "roots": [
                    "app/models"
                ],
                "files": {
                    "app/models/hotel.rb": "class Hotel; X = 1; end",
                    "app/models/hotel/pricing.rb": "class Hotel::Pricing; end"
                },
                "access": [
                    "Hotel",
                    "Hotel::X",
                    "Hotel::Pricing"
                ]
            },
            "expected_output": "constant=Hotel\nvalue=class\nconstant=Hotel::X\nvalue=1\nconstant=Hotel::Pricing\nvalue=class\n"
        }
    ]
}
```

---

### Feature 5: Duplicate Path Precedence

**As a developer, I want deterministic behavior when multiple roots contain the same inferred constant**, so duplicate files do not race or overwrite each other.

**Expected Behavior / Usage:**

*5.1 First Root Precedence — When multiple configured roots contain a source file for the same top-level constant, the file found through the earlier root takes precedence and later duplicates are shadowed.*

When multiple configured roots contain a source file for the same top-level constant, the file found through the earlier root takes precedence and later duplicates are shadowed.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_first_root_precedence.json`

```json
{
    "description": "When two roots contain files for the same top-level constant, load the first root file and leave later duplicates shadowed.",
    "cases": [
        {
            "input": {
                "operation": "multiple_root_precedence",
                "roots": [
                    "app/models",
                    "app/decorators"
                ],
                "files": {
                    "app/models/user.rb": "User = 'model'",
                    "app/decorators/user.rb": "User = 'decorator'"
                },
                "access": [
                    "User"
                ]
            },
            "expected_output": "constant=User\nvalue=model\n"
        }
    ]
}
```

---

### Feature 6: Ignored Paths

**As a developer, I want to exclude selected files and directories from management**, so tests, generated files, or optional paths are not loaded accidentally.

**Expected Behavior / Usage:**

*6.1 Ignore Files, Directories, and Globs — Configured ignored files, directories, and glob matches are excluded from lazy loading and eager loading.*

Configured ignored files, directories, and glob matches are excluded from lazy loading and eager loading. Non-ignored siblings remain available.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_ignore_files_and_directories.json`

```json
{
    "description": "Exclude configured files, directories, and glob matches from both lazy loading and eager loading.",
    "cases": [
        {
            "input": {
                "operation": "ignored_paths",
                "roots": [
                    "."
                ],
                "files": {
                    "x.rb": "X = true",
                    "y.rb": "Y = true",
                    "m/a.rb": "M::A = true"
                },
                "ignore": [
                    "y.rb",
                    "m"
                ],
                "access": [
                    "X",
                    "Y",
                    "M"
                ]
            },
            "expected_output": "constant=X\navailable=yes\nvalue=true\nconstant=Y\navailable=no\nconstant=M\navailable=no\n"
        }
    ]
}
```

---

### Feature 7: Eager Loading

**As a developer, I want an option to load all reachable managed files at once**, so deployments or checks can fail early and warm the application.

**Expected Behavior / Usage:**

*7.1 Eager Load Reachable Files — Eager loading evaluates all reachable managed source files under configured roots, including nested files, before explicit constant access.*

Eager loading evaluates all reachable managed source files under configured roots, including nested files, before explicit constant access. Observable side effects in those files occur during eager loading.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_eager_load_all_reachable_files.json`

```json
{
    "description": "Load every reachable source file under configured roots before any explicit constant access.",
    "cases": [
        {
            "input": {
                "operation": "eager_loading",
                "roots": [
                    "."
                ],
                "files": {
                    "app0.rb": "module App0; end",
                    "app0/foo.rb": "class App0::Foo; $global_signals['app0_foo'] = 'loaded'; end",
                    "app1/foo.rb": "class App1::Foo; end",
                    "app1/foo/bar/baz.rb": "class App1::Foo::Bar::Baz; $global_signals['app1_baz'] = 'loaded'; end"
                },
                "check_globals": [
                    "app0_foo",
                    "app1_baz"
                ],
                "access": [
                    "App0::Foo",
                    "App1::Foo::Bar::Baz"
                ]
            },
            "expected_output": "signal=app0_foo\nvalue=loaded\nsignal=app1_baz\nvalue=loaded\nconstant=App0::Foo\nvalue=class\nconstant=App1::Foo::Bar::Baz\nvalue=class\n"
        }
    ]
}
```

*7.2 Eager Load Exclusions Stay Lazy — Paths explicitly excluded from eager loading are skipped during eager loading but remain registered for later lazy access.*

Paths explicitly excluded from eager loading are skipped during eager loading but remain registered for later lazy access.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_eager_load_exclusions_remain_lazy.json`

```json
{
    "description": "Paths excluded from eager loading are not evaluated during eager loading but still remain available for later lazy loading.",
    "cases": [
        {
            "input": {
                "operation": "eager_loading_exclusions",
                "roots": [
                    "."
                ],
                "files": {
                    "foo.rb": "Foo = true",
                    "bar.rb": "Bar = true; $global_signals['bar'] = 'loaded'"
                },
                "exclude_from_eager_load": [
                    "bar.rb"
                ],
                "check_globals": [
                    "bar"
                ],
                "access": [
                    "Foo",
                    "Bar"
                ]
            },
            "expected_output": "signal=bar\nvalue=unset\nconstant=Foo\nvalue=true\nconstant=Bar\nvalue=true\n"
        }
    ]
}
```

---

### Feature 8: Reloading

**As a developer, I want managed constants to be refreshable during development**, so changed files can be read without restarting the process.

**Expected Behavior / Usage:**

*8.1 Reload Refreshes Loaded Values — When reloading is enabled before setup, a reload removes previously loaded managed constants and subsequent access reads the updated source contents.*

When reloading is enabled before setup, a reload removes previously loaded managed constants and subsequent access reads the updated source contents.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_reload_refreshes_values.json`

```json
{
    "description": "When reloading is enabled, a reload removes previously loaded objects and reads updated file contents on the next access.",
    "cases": [
        {
            "input": {
                "operation": "reload_updates_loaded_values",
                "roots": [
                    "."
                ],
                "files": {
                    "x.rb": "X = 1",
                    "y.rb": "module Y; end",
                    "y/a.rb": "Y::A = 1",
                    "z/a.rb": "Z::A = 1"
                },
                "before_access": [
                    "X",
                    "Y::A",
                    "Z::A"
                ],
                "updates": {
                    "x.rb": "X = 2",
                    "y/a.rb": "Y::A = 2",
                    "z/a.rb": "Z::A = 2"
                },
                "after_access": [
                    "X",
                    "Y::A",
                    "Z::A"
                ]
            },
            "expected_output": "before=X\nvalue=1\nbefore=Y::A\nvalue=1\nbefore=Z::A\nvalue=1\nafter=X\nvalue=2\nafter=Y::A\nvalue=2\nafter=Z::A\nvalue=2\n"
        }
    ]
}
```

*8.2 Reloading Disabled Error — If reloading was not enabled before setup, a reload request must fail with a normalized language-neutral error category.*

If reloading was not enabled before setup, a reload request must fail with a normalized language-neutral error category.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_reloading_disabled_error.json`

```json
{
    "description": "If reloading was not enabled before setup, requesting a reload reports a normalized reloading-disabled error.",
    "cases": [
        {
            "input": {
                "operation": "require_interaction",
                "enable_reloading": false,
                "roots": [
                    "."
                ],
                "files": {},
                "sequence": [
                    {
                        "action": "reload"
                    }
                ]
            },
            "expected_output": "error=reloading_disabled\n"
        }
    ]
}
```

---

### Feature 9: Unloading

**As a developer, I want loaded constants and generated namespaces to be removable**, so a loader can cleanly reset managed state.

**Expected Behavior / Usage:**

*9.1 Unload Removes Managed Constants — Unloading removes constants loaded from managed files and namespaces created from managed directories.*

Unloading removes constants loaded from managed files and namespaces created from managed directories. After unloading, those constants are no longer available from their parents.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_unload_removes_loaded_constants.json`

```json
{
    "description": "Unloading removes constants loaded from managed files and autovivified namespaces from their parents.",
    "cases": [
        {
            "input": {
                "operation": "unload_removes_loaded_constants",
                "roots": [
                    "."
                ],
                "files": {
                    "user.rb": "class User; end",
                    "admin/root.rb": "class Admin::Root; end"
                },
                "load": [
                    "User",
                    "Admin::Root"
                ],
                "check_absent": [
                    "User",
                    "Admin"
                ]
            },
            "expected_output": "constant=User\navailable=no\nconstant=Admin\navailable=no\n"
        }
    ]
}
```

---

### Feature 10: Interaction with Existing File Loading

**As a developer, I want manual file loading and managed lazy loading to stay consistent**, so requiring a managed file does not duplicate work.

**Expected Behavior / Usage:**

*10.1 Require Idempotence — Requiring a managed file through the normal file-loading mechanism reports that it loaded the file once, and a second require of the same path reports that the file was already loaded.*

Requiring a managed file through the normal file-loading mechanism reports that it loaded the file once, and a second require of the same path reports that the file was already loaded.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_require_idempotence.json`

```json
{
    "description": "A managed file required through the normal loader path returns loaded once, and a second require reports that it was already loaded.",
    "cases": [
        {
            "input": {
                "operation": "require_interaction",
                "roots": [
                    "."
                ],
                "load_paths": [
                    "."
                ],
                "files": {
                    "user.rb": "class User; end"
                },
                "sequence": [
                    {
                        "action": "require",
                        "path": "user"
                    },
                    {
                        "action": "require",
                        "path": "user"
                    }
                ]
            },
            "expected_output": "require=user\nloaded=yes\nrequire=user\nloaded=no\n"
        }
    ]
}
```

*10.2 Lazy Access Then Require Idempotence — After a managed constant is loaded by constant access, requiring the corresponding relative path reports that the file is already loaded.*

After a managed constant is loaded by constant access, requiring the corresponding relative path reports that the file is already loaded.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_autoload_then_require_idempotence.json`

```json
{
    "description": "After a managed constant is autoloaded by constant access, requiring the same relative path reports that it is already loaded.",
    "cases": [
        {
            "input": {
                "operation": "require_interaction",
                "roots": [
                    "."
                ],
                "load_paths": [
                    "."
                ],
                "files": {
                    "user.rb": "class User; end"
                },
                "sequence": [
                    {
                        "action": "access",
                        "constant": "User"
                    },
                    {
                        "action": "require",
                        "path": "user"
                    }
                ]
            },
            "expected_output": "constant=User\nvalue=class\nrequire=user\nloaded=no\n"
        }
    ]
}
```

---

### Feature 11: Normalized Loader Errors

**As a developer, I want contract-level errors that identify loader problems without leaking host runtime exception details**, so tests can be portable across implementations.

**Expected Behavior / Usage:**

*11.1 Missing Expected Constant — If a managed source file does not define the constant implied by its path, the adapter prints a normalized missing-constant error and the expected constant name.*

If a managed source file does not define the constant implied by its path, the adapter prints a normalized missing-constant error and the expected constant name.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_missing_expected_constant_error.json`

```json
{
    "description": "If a managed source file does not define the constant implied by its path, report the expected constant as a normalized contract error.",
    "cases": [
        {
            "input": {
                "operation": "invalid_expected_constant",
                "roots": [
                    "."
                ],
                "files": {
                    "typo.rb": "TyPo = 1"
                },
                "trigger": "access",
                "constant": "Typo"
            },
            "expected_output": "error=expected_constant_missing\nconstant=Typo\n"
        }
    ]
}
```

*11.2 Invalid Inferred Constant Name — If a file or directory segment infers an invalid constant name, setup prints a normalized invalid-name error, the invalid inferred name, and whether the bad entry was a file or directory.*

If a file or directory segment infers an invalid constant name, setup prints a normalized invalid-name error, the invalid inferred name, and whether the bad entry was a file or directory.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_invalid_inferred_constant_name_error.json`

```json
{
    "description": "If a path segment maps to an invalid constant name, setup reports a normalized invalid-name error for that path entry.",
    "cases": [
        {
            "input": {
                "operation": "invalid_constant_name",
                "roots": [
                    "."
                ],
                "files": {
                    "foo-bar.rb": "FooBar = 1"
                },
                "entry_type": "file"
            },
            "expected_output": "error=invalid_constant_name\nconstant=Foo-bar\nentry=file\n"
        }
    ]
}
```

---

### Feature 12: Root Directory Management

**As a developer, I want root directories to be registered and inspected predictably**, so multiple loaders can report what source roots they manage.

**Expected Behavior / Usage:**

*12.1 Root Registration and Aggregate Roots — Existing root directories are accepted, stored as absolute roots, and counted.*

Existing root directories are accepted, stored as absolute roots, and counted. The aggregate root list across loaders preserves the managed root basenames in registration order. Missing roots produce a normalized missing-root error.

**Test Cases:** `rcb_tests/public_test_cases/feature12_1_root_directory_registration.json`

```json
{
    "description": "Accept existing root directories as absolute managed roots and expose the aggregate list of roots across loaders.",
    "cases": [
        {
            "input": {
                "operation": "root_directory_registration",
                "scenario": "existing"
            },
            "expected_output": "root_registered=yes\nroot_count=1\nroot_absolute=yes\n"
        },
        {
            "input": {
                "operation": "root_directory_registration",
                "scenario": "all_dirs"
            },
            "expected_output": "managed_root_count=2\nmanaged_roots=loaderA,loaderB\n"
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
- similar to the standard underscore-to-camelcase convention used elsewhere
