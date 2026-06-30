## Product Requirement Document

# Kubernetes Operator Contract Toolkit - CRD, RBAC, Events, Leadership, and Test Harness Behavior

## Project Goal

Build a Kubernetes operator support library that allows developers to generate resource definitions, authorization rules, event records, leadership decisions, cache change signals, and in-process operator tests without hand-writing repetitive cluster integration boilerplate.

---

## Background & Problem

Without this library/tool, developers are forced to manually translate resource models into Kubernetes Custom Resource Definitions, keep OpenAPI schemas synchronized with model metadata, craft RBAC manifests, manage event updates, coordinate leader leases, and build custom test harnesses for controller lifecycle routing. This leads to repetitive manifests, inconsistent validation, fragile permission sets, and difficult-to-maintain tests.

With this library/tool, developers describe operator resources and handlers once, then receive deterministic Kubernetes-facing artifacts and observable runtime behavior that can be tested through a stable execution adapter.

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
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project size):
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

### Feature 1: CRD Identity Fields

**As a developer**, I want to generate the top-level identity for a custom resource description, so I can apply a predictable Kubernetes resource contract.

**Expected Behavior / Usage:**

Input selects a resource model category. Output is line-oriented and must include the resource-definition kind, generated metadata name, resource kind, list kind, singular name, plural name, and scope. Namespaced resources must report a namespaced scope and stable pluralized metadata naming.

**Test Cases:** `rcb_tests/public_test_cases/feature1_crd_identity.json`

```json
{
    "description": "Generates top-level Custom Resource Definition identity fields for a namespaced resource model.",
    "cases": [
        {
            "input": {
                "command": "crd_identity",
                "entity": "namespaced_spec"
            },
            "expected_output": "kind=CustomResourceDefinition\nmetadata_name=testspecentitys.kubeops.test.dev\nresource_kind=TestSpecEntity\nlist_kind=TestSpecEntityList\nsingular=testspecentity\nplural=testspecentitys\nscope=Namespaced\n"
        }
    ]
}
```

---

### Feature 2: Status Subresource Detection

**As a developer**, I want to know whether a generated resource definition exposes a status endpoint, so I can wire status updates only when the model supports them.

**Expected Behavior / Usage:**

Input selects a resource model category. Output reports `status_subresource=true` only when the model has a distinct status shape; models without status support must report `status_subresource=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_crd_status_subresource.json`

```json
{
    "description": "Reports whether a generated Custom Resource Definition exposes a status subresource based on the resource model shape.",
    "cases": [
        {
            "input": {
                "command": "crd_subresource",
                "entity": "status"
            },
            "expected_output": "status_subresource=true\n"
        },
        {
            "input": {
                "command": "crd_subresource",
                "entity": "namespaced_spec"
            },
            "expected_output": "status_subresource=false\n"
        }
    ]
}
```

---

### Feature 3.1: Scalar Schema Mapping

**As a developer**, I want to map scalar specification fields into OpenAPI property schemas, so I can publish precise type, format, and nullability information.

**Expected Behavior / Usage:**

Input selects a scalar field family. Output reports both the non-nullable and nullable field variants, including OpenAPI `type`, optional `format`, and nullable flag. Unknown or absent formats and nullable flags are rendered as `null`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_scalar_schema.json`

```json
{
    "description": "Maps scalar specification fields and nullable variants to OpenAPI schema type, format, and nullability.",
    "cases": [
        {
            "input": {
                "command": "crd_scalar_schema",
                "scalar": "Int"
            },
            "expected_output": "field=normalInt\ntype=integer\nformat=int32\nnullable=null\nfield=nullableInt\ntype=integer\nformat=int32\nnullable=true\n"
        },
        {
            "input": {
                "command": "crd_scalar_schema",
                "scalar": "String"
            },
            "expected_output": "field=normalString\ntype=string\nformat=null\nnullable=null\nfield=nullableString\ntype=string\nformat=null\nnullable=true\n"
        }
    ]
}
```

---

### Feature 3.2: Array Schema Mapping

**As a developer**, I want to map list-like specification fields into OpenAPI array schemas, so I can describe array item types and nullability consistently.

**Expected Behavior / Usage:**

Input selects an array-like property name. Output reports the property name, OpenAPI array type, item type, and nullable flag. Nullable collection fields must mark the array property nullable while retaining the same item schema.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_array_schema.json`

```json
{
    "description": "Maps list-like specification fields to OpenAPI array schemas with item type and field nullability.",
    "cases": [
        {
            "input": {
                "command": "crd_array_schema",
                "property": "stringArray"
            },
            "expected_output": "property=stringArray\ntype=array\nitem_type=string\nnullable=null\n"
        },
        {
            "input": {
                "command": "crd_array_schema",
                "property": "nullableStringArray"
            },
            "expected_output": "property=nullableStringArray\ntype=array\nitem_type=string\nnullable=true\n"
        }
    ]
}
```

---

### Feature 3.3: Structured Array Schema Mapping

**As a developer**, I want to map lists of structured objects into nested OpenAPI schemas, so I can preserve nested object shape for validation.

**Expected Behavior / Usage:**

Input selects a collection of structured objects. Output reports an array property whose items are OpenAPI objects and confirms that the nested `name` property is represented as a string.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_complex_array_schema.json`

```json
{
    "description": "Maps arrays of structured specification objects to OpenAPI array schemas with object items and nested property schemas.",
    "cases": [
        {
            "input": {
                "command": "crd_complex_array_schema",
                "property": "complexItemsEnumerable"
            },
            "expected_output": "property=complexItemsEnumerable\ntype=array\nitem_type=object\nitem_property_name_type=string\nnullable=null\n"
        }
    ]
}
```

---

### Feature 3.4: Validation Metadata Mapping

**As a developer**, I want to carry documentation and validation constraints into generated schemas, so I can enforce and document resource fields through the API server contract.

**Expected Behavior / Usage:**

Input selects a schema property carrying documentation or validation metadata. Output reports the property type and every supported metadata slot: description presence, external documentation presence, item count bounds, string length bounds, numeric multiple, regex pattern, and inclusive or exclusive numeric bounds. Unused slots are rendered as `null` or `false`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_validation_metadata.json`

```json
{
    "description": "Preserves validation and documentation metadata on generated OpenAPI schema properties.",
    "cases": [
        {
            "input": {
                "command": "crd_validation_metadata",
                "property": "items"
            },
            "expected_output": "property=items\ntype=array\ndescription_present=false\nexternal_docs_url_present=false\nexternal_docs_description_present=false\n[a specific minimum count for file uploads]\nmax_items=42\nmin_length=null\nmax_length=null\nmultiple_of=null\npattern=null\nminimum=null\nexclusive_minimum=null\nmaximum=null\nexclusive_maximum=null\n"
        },
        {
            "input": {
                "command": "crd_validation_metadata",
                "property": "length"
            },
            "expected_output": "property=length\ntype=string\ndescription_present=false\nexternal_docs_url_present=false\nexternal_docs_description_present=false\nmin_items=null\nmax_items=null\nmin_length=2\n[a standard maximum length for ID strings in this test suite]\nmultiple_of=null\npattern=null\nminimum=null\nexclusive_minimum=null\nmaximum=null\nexclusive_maximum=null\n"
        }
    ]
}
```

---

### Feature 3.5: Kubernetes Schema Extensions

**As a developer**, I want to emit Kubernetes-specific OpenAPI extension flags, so I can represent dynamic fields, embedded resources, and integer-or-string values correctly.

**Expected Behavior / Usage:**

Input selects a property requiring Kubernetes-specific schema semantics. Output reports whether normal nested properties are suppressed, whether unknown fields are preserved, whether the field is an embedded resource, whether it is an integer-or-string field, and equivalent item-level flags for arrays of embedded resources.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_kubernetes_schema_extensions.json`

```json
{
    "description": "Emits Kubernetes OpenAPI extension flags for dynamic fields, embedded resources, embedded resource arrays, and integer-or-string fields.",
    "cases": [
        {
            "input": {
                "command": "crd_extension_schema",
                "property": "intOrString"
            },
            "expected_output": "property=intOrString\ntype=null\nproperties_present=false\npreserve_unknown=null\nembedded_resource=null\nint_or_string=true\nitem_type=null\nitem_preserve_unknown=null\nitem_embedded_resource=null\n"
        },
        {
            "input": {
                "command": "crd_extension_schema",
                "property": "kubernetesObject"
            },
            "expected_output": "property=kubernetesObject\ntype=object\nproperties_present=false\npreserve_unknown=true\nembedded_resource=true\nint_or_string=null\nitem_type=null\nitem_preserve_unknown=null\nitem_embedded_resource=null\n"
        },
        {
            "input": {
                "command": "crd_extension_schema",
                "property": "pods"
            },
            "expected_output": "property=pods\ntype=array\nproperties_present=false\npreserve_unknown=null\nembedded_resource=null\nint_or_string=null\nitem_type=object\nitem_preserve_unknown=true\nitem_embedded_resource=true\n"
        }
    ]
}
```

---

### Feature 3.6: Schema Names and Error Categories

**As a developer**, I want to honor configured serialized property names and normalize unsupported schema inputs, so I can avoid leaking runtime exceptions while keeping schema failures actionable.

**Expected Behavior / Usage:**

Input either requests serialized-name inspection or attempts schema generation for an unsupported field type. Name inspection output must show that the configured wire name is present and the source property name is absent. Unsupported schema input must print only the neutral category `error=unsupported_schema_property_type`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_6_schema_errors_and_names.json`

```json
{
    "description": "Uses configured serialized property names in schemas and normalizes unsupported schema property types to a language-neutral error category.",
    "cases": [
        {
            "input": {
                "command": "crd_property_name"
            },
            "expected_output": "contains_name_from_attribute=true\ncontains_original_property_name=false\n"
        },
        {
            "input": {
                "command": "crd_invalid_type"
            },
            "expected_output": "error=unsupported_schema_property_type\n"
        }
    ]
}
```

---

### Feature 4: Printer Column Generation

**As a developer**, I want to add custom table-display columns to generated resource definitions, so I can show useful fields in command-line resource listings.

**Expected Behavior / Usage:**

Input requests the generated table-display column contract. Output contains one line per generated column in deterministic order, with column name, JSON path, OpenAPI type, and priority.

**Test Cases:** `rcb_tests/public_test_cases/feature4_printer_columns.json`

```json
{
    "description": "Adds custom printer column definitions to generated Custom Resource Definition versions.",
    "cases": [
        {
            "input": {
                "command": "crd_printer_columns"
            },
            "expected_output": "column=Age|path=.metadata.creationTimestamp|type=date|priority=0\ncolumn=Namespace|path=.metadata.namespace|type=string|priority=0\ncolumn=NormalInt|path=.spec.normalInt|type=integer|priority=1\ncolumn=OtherName|path=.spec.normalLong|type=integer|priority=0\ncolumn=NormalString|path=.spec.normalString|type=string|priority=0\n"
        }
    ]
}
```

---

### Feature 5: CRD Collection Generation

**As a developer**, I want to build a full collection of resource definitions from registered models, so I can install only intended resources with correct version storage semantics.

**Expected Behavior / Usage:**

Input requests the registered resource-definition collection summary. Output reports the total number of generated definitions, whether ignored resources leaked into the collection, and each definition with its served versions and single storage version.

**Test Cases:** `rcb_tests/public_test_cases/feature5_crd_collection_generation.json`

```json
{
    "description": "Builds a Custom Resource Definition collection from registered models, excluding ignored models and assigning storage versions.",
    "cases": [
        {
            "input": {
                "command": "crd_generation_summary"
            },
            "expected_output": "crd_count=5\ncontains_ignored=false\ncrd=AttributeVersionedEntity|versions=v2,v1|storage=v1\ncrd=TestClusterSpecEntity|versions=V1|storage=V1\ncrd=TestSpecEntity|versions=V1|storage=V1\ncrd=TestStatusEntity|versions=V1|storage=V1\ncrd=VersionedEntity|versions=v2,v2beta2,v1,v1beta1,v1alpha1|storage=v2\n"
        }
    ]
}
```

---

### Feature 6: RBAC Rule Generation

**As a developer**, I want to generate access-control rules from resource, webhook, and leader-election needs, so I can deploy an operator with the permissions it requires and no duplicated rule groups.

**Expected Behavior / Usage:**

Input selects an authorization scenario. Output reports the number of generated policy rules followed by deterministic `resources=...|verbs=...` lines. Leader-election scenarios include or omit lease and deployment rules according to settings; webhook scenarios include service and webhook-configuration rules; repeated compatible permissions are grouped by identical verbs.

**Test Cases:** `rcb_tests/public_test_cases/feature6_rbac_generation.json`

```json
{
    "description": "Generates role rules from resource permissions, webhook requirements, leader-election settings, and shared verb groups.",
    "cases": [
        {
            "input": {
                "command": "rbac",
                "scenario": "manager_with_leases"
            },
            "expected_output": "[the total number of RBAC permissions generated for the manager scenario]\nresources=deployments|verbs=get,list\nresources=deployments/status|verbs=get,patch,update\nresources=entitywithrbacs,leases|verbs=*\nresources=events|verbs=create,get,list,update\n"
        },
        {
            "input": {
                "command": "rbac",
                "scenario": "webhook"
            },
            "expected_output": "rule_count=3\nresources=events|verbs=create,get,list,update\nresources=services,validatingwebhookconfigurations,mutatingwebhookconfigurations|verbs=create,get,patch,update,delete\nresources=services/status|verbs=get,patch,update\n"
        },
        {
            "input": {
                "command": "rbac",
                "scenario": "merged_verbs"
            },
            "expected_output": "rule_count=3\nresources=events|verbs=create,get,list,update\nresources=rbactest1s,rbactest4s|verbs=get,update\nresources=rbactest2s,rbactest3s|verbs=delete\n"
        }
    ]
}
```

---

### Feature 7: Resource Cache Change Classification

**As a developer**, I want to cache resources by unique identifier and classify externally meaningful changes, so I can route lifecycle updates based on status or finalizer changes.

**Expected Behavior / Usage:**

Input describes a cache operation: missing lookup, comparison between previous and next resource representations, or removal. Output is either a neutral missing-resource error with the resource identifier, a comparison category plus identifier, or a removal confirmation followed by a missing lookup signal.

**Test Cases:** `rcb_tests/public_test_cases/feature7_resource_cache.json`

```json
{
    "description": "Caches resources by unique identifier, reports observable update categories, removes resources, and normalizes missing-resource lookups.",
    "cases": [
        {
            "input": {
                "command": "cache",
                "action": "get_missing",
                "uid": "foobar"
            },
            "expected_output": "error=resource_not_found\nuid=foobar\n"
        },
        {
            "input": {
                "command": "cache",
                "action": "compare",
                "first": {
                    "uid": "test",
                    "status": {
                        "text": "status"
                    }
                },
                "second": {
                    "uid": "test",
                    "status": {
                        "text": "status2"
                    }
                }
            },
            "expected_output": "comparison=StatusModified\nuid=test\n"
        },
        {
            "input": {
                "command": "cache",
                "action": "compare",
                "first": {
                    "uid": "test",
                    "finalizers": [
                        "f1"
                    ]
                },
                "second": {
                    "uid": "test",
                    "finalizers": [
                        "f2"
                    ]
                }
            },
            "expected_output": "comparison=FinalizersModified\nuid=test\n"
        },
        {
            "input": {
                "command": "cache",
                "action": "remove",
                "entity": {
                    "uid": "test"
                }
            },
            "expected_output": "removed_uid=test\nlookup_after_remove=resource_not_found\n"
        }
    ]
}
```

---

### Feature 8: Kubernetes Event Publication

**As a developer**, I want to publish event records and update repeated event counters, so I can record operator activity without creating duplicate event streams.

**Expected Behavior / Usage:**

Input selects direct publication, immediate resource event publication, or deferred publisher execution, with an optional existing event count. Output reports whether an event was saved, the deterministic event name, namespace, event uid, and resulting count. New events start at count 1; existing events preserve uid and increment count.

**Test Cases:** `rcb_tests/public_test_cases/feature8_event_publication.json`

```json
{
    "description": "Publishes Kubernetes events directly or from deferred publishers, creating new event records or updating existing event counters.",
    "cases": [
        {
            "input": {
                "command": "event",
                "mode": "publish",
                "existing_count": null
            },
            "expected_output": "saved=true\nname=MGODYZKPJ7QDVVCN2RUBXNOB6TD6XGCHDT46OMD5QG534WNV7LXIH3XZ4ISN746LUSVT57PH6KZCC7C62Z5QWYO2P4YJJHU6OJ2MRHY\nnamespace=test-ns\nuid=null\ncount=1\n"
        },
        {
            "input": {
                "command": "event",
                "mode": "publish",
                "existing_count": 4
            },
            "expected_output": "saved=true\nname=MGODYZKPJ7QDVVCN2RUBXNOB6TD6XGCHDT46OMD5QG534WNV7LXIH3XZ4ISN746LUSVT57PH6KZCC7C62Z5QWYO2P4YJJHU6OJ2MRHY\nnamespace=test-ns\nuid=existing-uid\ncount=5\n"
        }
    ]
}
```

---

### Feature 9: Leader Lease Evaluation

**As a developer**, I want to evaluate coordination leases and report leadership transitions, so I can run only the elected instance while handling contention and transient write failures.

**Expected Behavior / Usage:**

Input describes the current lease state and optional write error category. Output reports the number of leadership state changes and the resulting state lines. Missing or expired leases promote to leader when writes succeed; write conflicts during creation demote to candidate; valid leases held by another instance remain candidate; non-conflict write failures produce no state change.

**Test Cases:** `rcb_tests/public_test_cases/feature9_leader_election.json`

```json
{
    "description": "Checks a coordination lease and reports leadership state transitions for missing, self-held, expired, valid, and write-error scenarios.",
    "cases": [
        {
            "input": {
                "command": "leader",
                "lease": "missing"
            },
            "expected_output": "leadership_changes=1\nstate=Leader\n"
        },
        {
            "input": {
                "command": "leader",
                "lease": "missing",
                "write_error": "conflict"
            },
            "expected_output": "leadership_changes=1\nstate=Candidate\n"
        },
        {
            "input": {
                "command": "leader",
                "lease": "valid_other"
            },
            "expected_output": "leadership_changes=1\nstate=Candidate\n"
        }
    ]
}
```

---

### Feature 10: In-Process Operator Test Harness

**As a developer**, I want to exercise operator registration and lifecycle routing inside a test process, so I can verify handler wiring without a live cluster.

**Expected Behavior / Usage:**

Input requests either registration discovery or a synthetic lifecycle event. Registration output reports discovered entities, controllers, finalizers, validators, and mutators. Event output reports which handler counters were invoked for reconcile, status, delete, or finalization routing.

**Test Cases:** `rcb_tests/public_test_cases/feature10_operator_test_harness.json`

```json
{
    "description": "Provides an in-process operator harness that discovers registrations and routes resource lifecycle events to handlers.",
    "cases": [
        {
            "input": {
                "command": "operator_registration"
            },
            "expected_output": "entities=21\ncontrollers=1\nfinalizers=1\nvalidators=2\nmutators=1\n"
        },
        {
            "input": {
                "command": "operator_event",
                "event": "reconcile"
            },
            "expected_output": "reconciled=1\nstatus_modified=0\ndeleted=0\nfinalized=0\n"
        },
        {
            "input": {
                "command": "operator_event",
                "event": "finalize"
            },
            "expected_output": "reconciled=0\nstatus_modified=0\ndeleted=0\nfinalized=1\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_crd_identity.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_crd_identity@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- columns must be sorted alphabetically but keep the legacy BUG column last
- array items must also include the embedded resource pattern found in the non-primitive array examples
