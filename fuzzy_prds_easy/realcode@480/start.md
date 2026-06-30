## Product Requirement Document

# Portlet Descriptor Serialization Library — Bidirectional JSON/XML Mapping for Portlet Definitions

## Project Goal

Build a small serialization library that maps portlet descriptors to and from two interchange formats — JSON and XML — so developers can persist, transmit, and reload portlet definitions without hand-writing format-specific parsing and emitting code for every call site.

---

## Background & Problem

A *portlet descriptor* is an immutable record describing a single portlet: a portlet identifier, the fully-qualified name of the portlet's implementation class, and an ordered set of named initialization parameters (each a name/value pair). Descriptors are frequently grouped into a *portlet collection* (an ordered list of descriptors), which is the shape used by portlet deployment documents.

Without a shared library, every component that needs to read or write portlet definitions re-implements ad-hoc JSON/XML handling, leading to inconsistent field naming, brittle parsers, and duplicated boilerplate. This library provides one well-defined, symmetric contract: a single descriptor or a whole collection can be serialized to JSON or XML, and the same wire forms can be parsed back into descriptors. Serialization and parsing are mutual inverses, and parsing tolerates extra descriptive elements it does not model.

The wire vocabulary is fixed. In both formats the identifier uses the name `portlet-name`, the implementation class uses `portlet-class`, and each initialization parameter is a `name`/`value` pair grouped under `[a specific custom property name — check the portlet schema definition]`. A single descriptor's root is `portlet`; a collection's root is `portlet-app` (XML) or an object with a single `portlet` array (JSON).

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

### Feature 1: Serialize Portlet Descriptors To JSON

**As a developer**, I want to render portlet descriptors as JSON, so I can persist and transmit them in a widely-supported text format.

**Expected Behavior / Usage:**

*1.1 Single Descriptor To JSON — emit one descriptor as a JSON object*

A single descriptor is serialized into one JSON object whose keys are the fixed wire names. The identifier is emitted under `portlet-name`, the implementation class under `portlet-class`, and the initialization parameters under `[a specific custom property name — check the portlet schema definition]` as an array of objects, each holding a `name` and a `value`. The initialization parameters are emitted in the order they were supplied; the property order within the object is identifier, then class, then [a specific custom property name — check the portlet schema definition] array. The raw JSON string is printed followed by a single trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_record_to_json.json`

```json
{
    "description": "Serialize a single portlet record into its canonical JSON wire form. A portlet record carries a portlet identifier, a fully-qualified portlet implementation class name, and an ordered set of named initialization parameters. The serializer emits a single JSON object whose keys are the hyphenated wire names: the identifier under 'portlet-name', the class under 'portlet-class', and the initialization parameters under '[a specific custom property name — check the portlet schema definition]' as an array of objects, each holding a 'name' and a 'value'. Parameters are emitted in the order they were supplied. The raw JSON string is printed followed by a newline.",
    "cases": [
        {
            "input": {"op": "to_json", "target": "portlet", "portlet": {"portlet_id": "categories", "portlet_class": "com.liferay.portlet.StrutsPortlet", "init_params": {"view-action": "/ext/c", "param2": "param2.value"}}},
            "expected_output": "{\"portlet-name\":\"categories\",\"portlet-class\":\"com.liferay.portlet.StrutsPortlet\",\"[a specific custom property name — check the portlet schema definition]\":[{\"name\":\"view-action\",\"value\":\"/ext/c\"},{\"name\":\"param2\",\"value\":\"param2.value\"}]}\n"
        }
    ]
}
```

*1.2 Collection To JSON — emit an ordered list of descriptors as a JSON object*

A collection is serialized into one JSON object with a single key, `portlet`, whose value is an array of descriptor objects in the order supplied. Each array element has the same shape as a single descriptor (Feature 1.1). The raw JSON string is printed followed by a single trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_collection_to_json.json`

```json
{
    "description": "Serialize a collection of portlet records into its canonical JSON wire form. The collection is rendered as a single JSON object with one key, 'portlet', whose value is an array of portlet objects in the order supplied. Each element uses the same hyphenated wire names as an individual record ('portlet-name', 'portlet-class', and an '[a specific custom property name — check the portlet schema definition]' array of name/value objects). The raw JSON string is printed followed by a newline.",
    "cases": [
        {
            "input": {"op": "to_json", "target": "portlet_list", "portlets": [{"portlet_id": "categories", "portlet_class": "com.liferay.portlet.StrutsPortlet", "init_params": {"view-action": "/ext/c", "param2": "param2.value"}}]},
            "expected_output": "{\"portlet\":[{\"portlet-name\":\"categories\",\"portlet-class\":\"com.liferay.portlet.StrutsPortlet\",\"[a specific custom property name — check the portlet schema definition]\":[{\"name\":\"view-action\",\"value\":\"/ext/c\"},{\"name\":\"param2\",\"value\":\"param2.value\"}]}]}\n"
        }
    ]
}
```

---

### Feature 2: Parse A Portlet Collection From JSON

**As a developer**, I want to rebuild a portlet collection from its JSON wire form, so I can reload definitions that were previously serialized.

**Expected Behavior / Usage:**

The input payload is a JSON string in the canonical collection wire form (an object with a `portlet` array; each element keyed by `portlet-name`, `portlet-class`, and `[a specific custom property name — check the portlet schema definition]`). The parser reconstructs every descriptor, recovering its identifier, implementation class, and initialization parameters as a name-to-value mapping. The reconstructed state is reported as a deterministic textual dump: a `portlets=<count>` line, then for each descriptor in document order a `[i] id=...` line, a `[i] class=...` line, a `[i] init_count=...` line, and one `[i] init.<name>=<value>` line per initialization parameter with parameter names sorted in ascending order. Every line, including the last, ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_collection_from_json.json`

```json
{
    "description": "Parse a JSON wire document back into a portlet collection and report the reconstructed domain state. The input payload is a JSON string in the canonical wire form (a 'portlet' array of objects keyed by 'portlet-name', 'portlet-class', and '[a specific custom property name — check the portlet schema definition]'). The parser must rebuild each portlet record, exposing its identifier, its implementation class, and its initialization parameters as a name-to-value mapping. The reconstructed state is printed as a deterministic dump: the number of portlets, then for each portlet (in document order) its identifier, class, parameter count, and each parameter as a 'init.<name>=<value>' line with parameter names in ascending order.",
    "cases": [
        {
            "input": {"op": "from_json", "target": "portlet_list", "payload": "{\"portlet\":[{\"portlet-name\":\"categories\",\"portlet-class\":\"com.liferay.portlet.StrutsPortlet\",\"[a specific custom property name — check the portlet schema definition]\":[{\"name\":\"view-action\",\"value\":\"/ext/c\"},{\"name\":\"param2\",\"value\":\"param2.value\"}]}]}"},
            "expected_output": "portlets=1\n[0] id=categories\n[0] class=com.liferay.portlet.StrutsPortlet\n[0] init_count=2\n[0] init.param2=param2.value\n[0] init.view-action=/ext/c\n"
        }
    ]
}
```

---

### Feature 3: Serialize Portlet Descriptors To XML

**As a developer**, I want to render portlet descriptors as XML, so I can produce portlet deployment documents.

**Expected Behavior / Usage:**

*3.1 Single Descriptor To XML — emit one descriptor as a `<portlet>` element*

A single descriptor is serialized into a `<portlet>` element containing a `<portlet-name>` element for the identifier, a `<portlet-class>` element for the implementation class, and one `<[a specific custom property name — check the portlet schema definition]>` element per initialization parameter, each wrapping a `<name>` and a `<value>` element. The `<[a specific custom property name — check the portlet schema definition]>` elements are emitted directly under `<portlet>` (they are not enclosed in any wrapper element) and appear in the order supplied. The raw XML string is printed followed by a single trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_record_to_xml.json`

```json
{
    "description": "Serialize a single portlet record into its canonical XML wire form. The record is rendered as a '<portlet>' element containing a '<portlet-name>' element for the identifier, a '<portlet-class>' element for the implementation class, and one '<[a specific custom property name — check the portlet schema definition]>' element per initialization parameter, each wrapping a '<name>' and a '<value>' element. Initialization parameters appear in the order supplied and [a specific custom property name — check the portlet schema definition] elements are not wrapped in any container element. The raw XML string is printed followed by a newline.",
    "cases": [
        {
            "input": {"op": "to_xml", "target": "portlet", "portlet": {"portlet_id": "categories", "portlet_class": "com.liferay.portlet.StrutsPortlet", "init_params": {"view-action": "/ext/c", "param2": "param2.value"}}},
            "expected_output": "<portlet><portlet-name>categories</portlet-name><portlet-class>com.liferay.portlet.StrutsPortlet</portlet-class><[a specific custom property name — check the portlet schema definition]><name>view-action</name><value>/ext/c</value></[a specific custom property name — check the portlet schema definition]><[a specific custom property name — check the portlet schema definition]><name>param2</name><value>param2.value</value></[a specific custom property name — check the portlet schema definition]></portlet>\n"
        }
    ]
}
```

*3.2 Collection To XML — emit an ordered list of descriptors under a `<portlet-app>` root*

A collection is serialized into a single `<portlet-app>` root element containing one `<portlet>` child per descriptor, in the order supplied. Each `<portlet>` child has the same structure as a single descriptor (Feature 3.1). The raw XML string is printed followed by a single trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_collection_to_xml.json`

```json
{
    "description": "Serialize a collection of portlet records into its canonical XML wire form. The collection is rendered as a single '<portlet-app>' root element containing one '<portlet>' child per record, in the order supplied. Each '<portlet>' child uses the same structure as an individual record ('<portlet-name>', '<portlet-class>', and unwrapped '<[a specific custom property name — check the portlet schema definition]>' elements). The raw XML string is printed followed by a newline.",
    "cases": [
        {
            "input": {"op": "to_xml", "target": "portlet_list", "portlets": [{"portlet_id": "categories", "portlet_class": "com.liferay.portlet.StrutsPortlet", "init_params": {"view-action": "/ext/c", "param2": "param2.value"}}]},
            "expected_output": "<portlet-app><portlet><portlet-name>categories</portlet-name><portlet-class>com.liferay.portlet.StrutsPortlet</portlet-class><[a specific custom property name — check the portlet schema definition]><name>view-action</name><value>/ext/c</value></[a specific custom property name — check the portlet schema definition]><[a specific custom property name — check the portlet schema definition]><name>param2</name><value>param2.value</value></[a specific custom property name — check the portlet schema definition]></portlet></portlet-app>\n"
        }
    ]
}
```

---

### Feature 4: Parse Portlet Descriptors From XML

**As a developer**, I want to rebuild portlet descriptors from their XML wire form, so I can read portlet deployment documents into domain objects.

**Expected Behavior / Usage:**

*4.1 Single Descriptor From XML — parse one `<portlet>` element*

The input payload is an XML string with a `<portlet>` root containing `<portlet-name>`, `<portlet-class>`, and one or more `<[a specific custom property name — check the portlet schema definition]>` elements. The parser reconstructs the descriptor, recovering its identifier, implementation class, and initialization parameters. The reconstructed state is reported as a deterministic dump: an `id=...` line, a `class=...` line, an `init_count=...` line, then one `init.<name>=<value>` line per parameter with parameter names sorted ascending. Every line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_record_from_xml.json`

```json
{
    "description": "Parse a single portlet's XML wire document back into a portlet record and report the reconstructed domain state. The input payload is an XML string with a '<portlet>' root containing '<portlet-name>', '<portlet-class>', and one or more '<[a specific custom property name — check the portlet schema definition]>' elements. The parser must rebuild the record, exposing its identifier, its implementation class, and its initialization parameters as a name-to-value mapping. The reconstructed state is printed as a deterministic dump: the identifier, the class, the parameter count, then each parameter as a 'init.<name>=<value>' line with parameter names in ascending order.",
    "cases": [
        {
            "input": {"op": "from_xml", "target": "portlet", "payload": "<portlet><portlet-name>categories</portlet-name><portlet-class>com.liferay.portlet.StrutsPortlet</portlet-class><[a specific custom property name — check the portlet schema definition]><name>view-action</name><value>/ext/c</value></[a specific custom property name — check the portlet schema definition]><[a specific custom property name — check the portlet schema definition]><name>param2</name><value>param2.value</value></[a specific custom property name — check the portlet schema definition]></portlet>"},
            "expected_output": "id=categories\nclass=com.liferay.portlet.StrutsPortlet\ninit_count=2\ninit.param2=param2.value\ninit.view-action=/ext/c\n"
        }
    ]
}
```

*4.2 Collection From XML — parse a `<portlet-app>` document, tolerating unknown elements*

The input payload is an XML string with a `<portlet-app>` root containing one or more `<portlet>` elements. A `<portlet>` may carry additional descriptive elements that are not part of the descriptor model (for example a display name or a resource bundle); such unknown elements must be tolerated and silently ignored rather than causing a failure. The parser reconstructs every descriptor and reports the collection as the same deterministic dump used in Feature 2 (a `portlets=<count>` line, then per descriptor in document order its `id`, `class`, `init_count`, and sorted `init.<name>=<value>` lines).

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_collection_from_xml.json`

```json
{
    "description": "Parse a portlet-collection XML wire document back into a portlet collection and report the reconstructed domain state. The input payload is an XML string with a '<portlet-app>' root containing one or more '<portlet>' elements. Each portlet may also carry descriptive elements that are not part of the portlet record model (such as a display name or a resource bundle); these unknown elements must be tolerated and ignored without error. The parser rebuilds every portlet, exposing its identifier, its implementation class, and its initialization parameters. The reconstructed state is printed as a deterministic dump: the number of portlets, then for each portlet (in document order) its identifier, class, parameter count, and each parameter as a 'init.<name>=<value>' line with parameter names in ascending order.",
    "cases": [
        {
            "input": {"op": "from_xml", "target": "portlet_list", "payload": "<portlet-app><portlet><portlet-name>categories</portlet-name><display-name>Category Manager</display-name><portlet-class>com.liferay.portlet.StrutsPortlet</portlet-class><[a specific custom property name — check the portlet schema definition]><name>view-action</name><value>/ext/categories/view_categories</value></[a specific custom property name — check the portlet schema definition]><resource-bundle>com.liferay.portlet.StrutsResourceBundle</resource-bundle></portlet><portlet><portlet-name>site-browser</portlet-name><portlet-class>com.liferay.portlet.StrutsPortlet</portlet-class><[a specific custom property name — check the portlet schema definition]><name>view-action</name><value>/ext/browser/view_browser</value></[a specific custom property name — check the portlet schema definition]></portlet><portlet><portlet-name>content</portlet-name><portlet-class>com.liferay.portlet.StrutsPortlet</portlet-class><[a specific custom property name — check the portlet schema definition]><name>view-action</name><value>/ext/contentlet/view_contentlets</value></[a specific custom property name — check the portlet schema definition]></portlet></portlet-app>"},
            "expected_output": "portlets=3\n[0] id=categories\n[0] class=com.liferay.portlet.StrutsPortlet\n[0] init_count=1\n[0] init.view-action=/ext/categories/view_categories\n[1] id=site-browser\n[1] class=com.liferay.portlet.StrutsPortlet\n[1] init_count=1\n[1] init.view-action=/ext/browser/view_browser\n[2] id=content\n[2] class=com.liferay.portlet.StrutsPortlet\n[2] init_count=1\n[2] init.view-action=/ext/contentlet/view_contentlets\n"
        }
    ]
}
```

*4.3 Collection XML Round-Trip — serialize via the collection's own entry point, then parse via the builder*

A collection is rendered to XML using the collection value's own serialization entry point, then a fresh collection is rebuilt from that XML using the collection builder's parse entry point. This verifies the serialize/parse pair is mutually consistent: a value serialized and then parsed yields an equivalent value. The rebuilt collection is reported using the same deterministic dump as Feature 2 / Feature 4.2.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_collection_roundtrip.json`

```json
{
    "description": "Round-trip a portlet collection through its own XML representation: take an in-memory collection, render it to XML using the collection's own serialization entry point, then rebuild a fresh collection from that XML using the collection builder's parse entry point. This verifies the serialize/parse pair is mutually consistent (a value serialized and then parsed yields an equivalent value). The rebuilt collection's state is printed as a deterministic dump: the number of portlets, then for each portlet (in order) its identifier, class, parameter count, and each parameter as a 'init.<name>=<value>' line with parameter names in ascending order.",
    "cases": [
        {
            "input": {"op": "from_xml_roundtrip", "target": "portlet_list", "portlets": [{"portlet_id": "categories", "portlet_class": "com.liferay.portlet.StrutsPortlet", "init_params": {"view-action": "/ext/c", "param2": "param2.value"}}]},
            "expected_output": "portlets=1\n[0] id=categories\n[0] class=com.liferay.portlet.StrutsPortlet\n[0] init_count=2\n[0] init.param2=param2.value\n[0] init.view-action=/ext/c\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic (the descriptor model, the collection model, and the JSON/XML serialization helper) must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-leaf-feature contracts above. The request's `op` selects behavior (`to_json`, `to_xml`, `from_json`, `from_xml`, `from_xml_roundtrip`) and its `target` selects the granularity (`portlet` for a single descriptor, `portlet_list` for a collection). For serialization operations the descriptor data arrives as structured objects (`portlet` / `portlets`, each with `portlet_id`, `portlet_class`, and an ordered `init_params` map); for parse operations the wire document arrives as a `payload` string. Serialization prints the raw wire string followed by a newline; parse operations print the deterministic state dump described above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- ensure the trailing newline matches the format of the legacy log output
