## Product Requirement Document

# Value Enumeration Toolkit — Named Value Sets, Human Labels, and Model Attribute Binding

## Project Goal

Build a reusable toolkit that lets developers declare a fixed set of named [human-readable label sort order] once and then work with them safely throughout an application — looking [human-readable label sort order] up by name or key, rendering human-readable labels (with localization), serializing them, and binding a model attribute to such a set so the attribute gains description, state-check, mutation, query-filter, and validation behavior automatically.

---

## Background & Problem

Applications constantly model small closed sets of [human-readable label sort order]: statuses, types, roles, modes. Without a dedicated tool, developers scatter raw literals and magic strings across the codebase, hand-write parallel lookup tables for human labels, and reimplement the same "is it this status?" / "set it to that status" / "only allow these [human-readable label sort order]" logic on every model. This is repetitive, error-prone, and hard to localize.

This toolkit centralizes the definition of a value set and exposes a rich, consistent interface around it. An *entry* in a value set has a symbolic *key* (e.g. `value_1`), a stored *value* (e.g. `"1"`), and a human *label* (e.g. `"Hey, I am 1!"`). When only a value is supplied for an entry, the label defaults to a title-cased rendering of the key, and labels can be overridden per locale. Each entry is also exposed as an accessible *constant* whose identifier is derived from the key. Beyond the value set itself, the toolkit can bind one of a host object's attributes to a value set, generating helpers for description, boolean state checks, value mutation, per-value query filters, per-value strategy objects, and model validations.

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

### Feature 1: Declaring A Value Set And Its Generated Constants

**As a developer**, I want to declare a value set from a key→value (optionally key→[value, label]) map or from a bare list of tokens, and get one accessible constant per entry, so I can reference [human-readable label sort order] by stable names instead of magic literals.

**Expected Behavior / Usage:**

A definition supplies either a `map` form (each entry key mapped to a value, or to a `[value, label]` pair) or a `list` form (a bare sequence of tokens, where each token becomes both the entry key and — title-cased — its default label, with the token itself as the value). Every entry is exposed as a constant. The constant identifier is derived from the entry key by upcasing it and replacing each dash or whitespace run with a single underscore; the value is preserved verbatim, including embedded capitalization, dashes, or spaces. The output lists each constant identifier and its value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_constants.json`

```json
{
    "description": "Define a set of named entries and read back the auto-generated public constants. From a definition that maps each entry's symbolic key to a value (optionally paired with a human label) — or from a bare list of raw tokens — the toolkit exposes one accessible constant per entry whose value is the entry's value. The constant identifier is derived from the entry key by upcasing it and replacing every dash or whitespace run with an underscore, while the value itself is preserved verbatim (including embedded capitalization, dashes, or spaces).",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "named_constants", "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "VALUE_1=1\nVALUE_2=2\nVALUE_3=3\n"},
        {"input": {"action": "[human-readable label sort order]", "query": "named_constants", "enum": {"form": "list", "[human-readable label sort order]": ["pt-BR"]}}, "expected_output": "PT_BR=pt-BR\n"}
    ]
}
```

---

### Feature 2: Inspecting The Value Set

**As a developer**, I want to read back the structure of a declared value set in several shapes, so I can drive UIs, range checks, and bookkeeping from a single source of truth.

**Expected Behavior / Usage:**

*2.1 Ordered [human-readable label sort order] — list every value*

Return every value, one per line, in the resolved order. By default the order is declaration order; a definition may request a default ordering strategy: by value, by key, by label, or explicitly none (declaration order). The output is the list of [human-readable label sort order].

**Test Cases:** `rcb_tests/public_test_cases/feature2_list.json`

```json
{
    "description": "Return the ordered collection of all [human-readable label sort order] defined in the enumeration. By default the [human-readable label sort order] are listed in the order the entries were declared. A definition may also request a default ordering strategy: order by value, by entry key, by human label, or explicitly none (declaration order). The output is the list of [human-readable label sort order], one per line, in the resolved order.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "[human-readable label sort order]", "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "1\n2\n3\n"},
        {"input": {"action": "[human-readable label sort order]", "query": "[human-readable label sort order]", "enum": {"form": "map", "[human-readable label sort order]": "name", "[human-readable label sort order]": {"foo": ["1", "xyz"], "bar": ["2", "fgh"], "omg": ["3", "abc"], "zomg": ["0", "jkl"]}}}, "expected_output": "2\n1\n3\n0\n"}
    ]
}
```

*2.2 Full definition — every entry's key, value, and label*

Report the complete specification: for every entry, in declaration order, its key together with its value and label.

**Test Cases:** `rcb_tests/public_test_cases/feature3_enumeration.json`

```json
{
    "description": "Return the full internal specification of the enumeration: for every entry, its symbolic key together with the value and human label associated with it. Entries are reported in declaration order, one line per entry, exposing the key, the value, and the label.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "definition", "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "key=value_1 value=1 label=Hey, I am 1!\nkey=value_2 value=2 label=Hey, I am 2!\nkey=value_3 value=3 label=Hey, I am 3!\n"}
    ]
}
```

*2.3 Count — number of entries*

Report how many entries the value set contains.

**Test Cases:** `rcb_tests/public_test_cases/feature4_length.json`

```json
{
    "description": "Report how many entries the enumeration contains. The output is the count of defined entries.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "count", "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "count=3\n"}
    ]
}
```

*2.4 Value range — inclusive interval of the [human-readable label sort order]*

Return the inclusive interval spanning the smallest to the largest value.

**Test Cases:** `rcb_tests/public_test_cases/feature9_range.json`

```json
{
    "description": "Return an inclusive interval spanning the enumeration's [human-readable label sort order], from the smallest value to the largest. The output reports the lower and upper bounds of that interval.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "[text-based range boundaries]", "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "range_begin=1 range_end=3\n"}
    ]
}
```

*2.5 Keys — the symbolic keys*

Return the list of entry keys used to define the value set, in declaration order.

**Test Cases:** `rcb_tests/public_test_cases/feature14_keys.json`

```json
{
    "description": "Return the list of entry keys used to define the enumeration, in declaration order, one key per line.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "keys", "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "value_1\nvalue_2\nvalue_3\n"}
    ]
}
```

---

### Feature 3: Human Labels And Localization

**As a developer**, I want to render [human-readable label sort order] as human-readable labels (and serialize them), with optional per-locale overrides, so I can present and export the value set without duplicating label tables.

**Expected Behavior / Usage:**

*3.1 Label/value pairs*

Produce a list of human-label / value pairs (label first, value second) suitable for selection widgets, following the resolved ordering. An entry declared without an explicit label falls back to a title-cased rendering of its key. One pair per line.

**Test Cases:** `rcb_tests/public_test_cases/feature5_to_a.json`

```json
{
    "description": "Produce a list of human-label / value pairs suitable for populating selection widgets. For each entry, the pair is the entry's human label followed by its value. When an entry was declared with only a value and no explicit label, the label defaults to a title-cased rendering of the entry key. The pairs follow the enumeration's resolved ordering (declaration order by default, or the requested ordering strategy: by value, by key, by label, or none). One pair is emitted per line.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "labeled_[human-readable label sort order]", "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "label=Hey, I am 1! value=1\nlabel=Hey, I am 2! value=2\nlabel=Hey, I am 3! value=3\n"},
        {"input": {"action": "[human-readable label sort order]", "query": "labeled_[human-readable label sort order]", "enum": {"form": "map", "[human-readable label sort order]": "translation", "[human-readable label sort order]": {"foo": ["1", "xyz"], "bar": ["2", "fgh"], "omg": ["3", "abc"], "zomg": ["0", "jkl"]}}}, "expected_output": "label=abc value=3\nlabel=fgh value=2\nlabel=jkl value=0\nlabel=xyz value=1\n"}
    ]
}
```

*3.2 Localized label/value pairs*

When entries are declared without explicit labels, resolve each label against a per-locale override table keyed by entry key under the active locale; entries with no override fall back to the title-cased key. Switching the active locale changes the resolved labels.

**Test Cases:** `rcb_tests/public_test_cases/feature6_to_a_translation.json`

```json
{
    "description": "Produce the human-label / value pairs while honoring a localization table. For entries declared without an explicit label, the human label is resolved against a per-locale override table keyed by entry key under the active locale; entries with no matching override fall back to a title-cased rendering of the key. Switching the active locale changes the resolved labels accordingly. One pair is emitted per line.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "labeled_[human-readable label sort order]", "enum": {"form": "map", "name": "Sample", "[human-readable label sort order]": {"value_one": "1", "value_two": "2"}, "label_overrides": {"en": {"value_one": "First Value"}, "pt": {"value_one": "Primeiro Valor"}}, "locale": "en"}}, "expected_output": "label=First Value value=1\nlabel=Value Two value=2\n"},
        {"input": {"action": "[human-readable label sort order]", "query": "labeled_[human-readable label sort order]", "enum": {"form": "map", "name": "Sample", "[human-readable label sort order]": {"value_one": "1", "value_two": "2"}, "label_overrides": {"en": {"value_one": "First Value"}, "pt": {"value_one": "Primeiro Valor"}}, "locale": "pt"}}, "expected_output": "label=Primeiro Valor value=1\nlabel=Value Two value=2\n"}
    ]
}
```

*3.3 All labels*

Return every entry's human label, in declaration order, one per line (each being the supplied label or the title-cased fallback).

**Test Cases:** `rcb_tests/public_test_cases/feature10_labels.json`

```json
{
    "description": "Return the complete list of human labels for the enumeration, in declaration order, one label per line. Each label is the entry's human label (or the title-cased fallback derived from the key when none was supplied).",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "labels", "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "Hey, I am 1!\nHey, I am 2!\nHey, I am 3!\n"}
    ]
}
```

*3.4 Translate a single value*

Given one value, return the human label associated with it, resolved against the active-locale override table.

**Test Cases:** `rcb_tests/public_test_cases/feature8_translate_value.json`

```json
{
    "description": "Given a single value, return the human label associated with that value, resolved against the active-locale override table. The input names the value to translate; the output is the resolved label for the matching entry.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "translate", "args": ["1"], "enum": {"form": "map", "name": "Sample", "[human-readable label sort order]": {"value_one": "1", "value_two": "2"}, "label_overrides": {"pt": {"value_one": "Primeiro Valor"}}, "locale": "pt"}}, "expected_output": "label=Primeiro Valor\n"}
    ]
}
```

*3.5 JSON serialization*

Serialize the value set to a JSON array of objects, one per entry in declaration order, each carrying a `value` and a `label`. Labels honor the active-locale override table; when the active locale has no override table at all, every label uses the title-cased fallback.

**Test Cases:** `rcb_tests/public_test_cases/feature7_to_json.json`

```json
{
    "description": "Serialize the enumeration to a JSON array of objects, one per entry in declaration order, where each object carries a value field and a label field. The label honors the active-locale override table when present and otherwise falls back to a title-cased rendering of the entry key; when the active locale has no override table at all, every label uses the title-cased fallback. The output is the JSON text.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "json", "enum": {"form": "map", "name": "Sample", "[human-readable label sort order]": {"value_one": "1", "value_two": "2"}, "locale": "inexistent"}}, "expected_output": "[{\"value\":\"1\",\"label\":\"Value One\"},{\"value\":\"2\",\"label\":\"Value Two\"}]\n"},
        {"input": {"action": "[human-readable label sort order]", "query": "json", "enum": {"form": "map", "name": "Sample", "[human-readable label sort order]": {"value_one": "1", "value_two": "2"}, "label_overrides": {"pt": {"value_one": "Primeiro Valor"}}, "locale": "pt"}}, "expected_output": "[{\"value\":\"1\",\"label\":\"Primeiro Valor\"},{\"value\":\"2\",\"label\":\"Value Two\"}]\n"}
    ]
}
```

---

### Feature 4: Looking Values And Keys Up

**As a developer**, I want safe lookups between constants, keys, and [human-readable label sort order], returning an absent marker (never an error) when nothing matches, so I can resolve identifiers defensively.

**Expected Behavior / Usage:**

*4.1 Values by constant identifiers*

Given a list of constant identifiers, resolve each to the value of the matching entry, preserving order; an unknown identifier resolves to an absent marker rather than raising. One resolution per line.

**Test Cases:** `rcb_tests/public_test_cases/feature11_[human-readable label sort order]_by_constant_names.json`

```json
{
    "description": "Given a list of constant identifiers, resolve each to the value of the matching entry, preserving the requested order. An identifier that does not correspond to any defined constant resolves to an absent marker rather than raising. One resolution is emitted per line.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "[human-readable label sort order]_by_constant_names", "args": ["VALUE_1", "VALUE_2"], "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "1\n2\n"},
        {"input": {"action": "[human-readable label sort order]", "query": "[human-readable label sort order]_by_constant_names", "args": ["VALUE_1", "THIS_IS_WRONG"], "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "1\nnil\n"}
    ]
}
```

*4.2 Value by a single constant identifier*

Given one constant identifier, return the matching entry's value, or an absent marker when none matches.

**Test Cases:** `rcb_tests/public_test_cases/feature12_value_by_constant_name.json`

```json
{
    "description": "Given a single constant identifier, return the value of the matching entry. When no constant matches the supplied identifier, the result is an absent marker rather than an error.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "value_by_constant_name", "args": ["VALUE_1"], "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "value=1\n"},
        {"input": {"action": "[human-readable label sort order]", "query": "value_by_constant_name", "args": ["THIS_IS_WRONG"], "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "value=nil\n"}
    ]
}
```

*4.3 Value by entry key*

Given an entry key (in plain textual form), return the entry's value. An unknown key — and an absent (null) key — yield an absent marker.

**Test Cases:** `rcb_tests/public_test_cases/feature13_value_by_key.json`

```json
{
    "description": "Given an entry key, return the value of that entry. A key that is not part of the enumeration yields an absent marker, and so does an absent (null) key. The lookup accepts the key in its plain textual form.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "value_by_key", "args": ["value_1"], "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "value=1\n"},
        {"input": {"action": "[human-readable label sort order]", "query": "value_by_key", "args": [null], "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "value=nil\n"}
    ]
}
```

*4.4 Key by value*

Given a value, return the entry key mapping to it, or an absent marker when the value is not present.

**Test Cases:** `rcb_tests/public_test_cases/feature15_key_by_value.json`

```json
{
    "description": "Given a value, return the entry key that maps to it. A value that is not present in the enumeration yields an absent marker.",
    "cases": [
        {"input": {"action": "[human-readable label sort order]", "query": "key_by_value", "args": ["1"], "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "key=value_1\n"},
        {"input": {"action": "[human-readable label sort order]", "query": "key_by_value", "args": ["foo"], "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "key=nil\n"}
    ]
}
```

---

### Feature 5: Binding A Model Attribute To A Value Set

**As a developer**, I want to associate one of a host object's attributes with a value set, so the attribute automatically gains description, state-check, mutation, strategy-object, query-filter, and validation behavior.

**Expected Behavior / Usage:**

*5.1 Attribute label — describe the attribute's current value*

Bind an attribute to a value set; the attribute's human description is the label of the entry whose value equals the attribute's current value (the supplied label, or a title-cased fallback). When the attribute holds no value, the description is absent.

**Test Cases:** `rcb_tests/public_test_cases/feature16_attribute_label.json`

```json
{
    "description": "Associate one of a host object's attributes with an enumeration and derive a human-readable description of the attribute's current value. Given the attribute's current value, the description is the human label of the matching entry (the entry's supplied label, or a title-cased fallback derived from the key when none was supplied). When the attribute holds no value, the description is absent.",
    "cases": [
        {"input": {"action": "attribute_label", "attribute": "foobar", "value": "2", "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "label=Hey, I am 2!\n"},
        {"input": {"action": "attribute_label", "attribute": "foobar", "value": null, "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "label=nil\n"}
    ]
}
```

*5.2 Localized attribute label*

The attribute's description follows the active locale when the matching entry's label is resolved through the override table: the same value yields different descriptions under different active locales.

**Test Cases:** `rcb_tests/public_test_cases/feature17_attribute_label_translation.json`

```json
{
    "description": "Derive the human-readable description of an associated attribute's value while honoring localization. For entries whose label is resolved through the active-locale override table, the attribute description follows the locale: the same value yields different descriptions under different active locales.",
    "cases": [
        {"input": {"action": "attribute_label", "attribute": "foobar", "value": "1", "enum": {"form": "map", "name": "Sample", "[human-readable label sort order]": {"value_one": "1", "value_two": "2"}, "label_overrides": {"en": {"value_one": "First Value"}, "pt": {"value_one": "Primeiro Valor"}}, "locale": "en"}}, "expected_output": "label=First Value\n"},
        {"input": {"action": "attribute_label", "attribute": "foobar", "value": "1", "enum": {"form": "map", "name": "Sample", "[human-readable label sort order]": {"value_one": "1", "value_two": "2"}, "label_overrides": {"en": {"value_one": "First Value"}, "pt": {"value_one": "Primeiro Valor"}}, "locale": "pt"}}, "expected_output": "label=Primeiro Valor\n"}
    ]
}
```

*5.3 State checks — per-value boolean predicates*

Optionally generate per-entry boolean checks on the host object reporting whether the attribute currently equals a given entry's value; exactly the matching entry's check is true. An optional prefix derived from the attribute name may be prepended. When check generation is not requested, no such checks exist.

**Test Cases:** `rcb_tests/public_test_cases/feature18_state_checks.json`

```json
{
    "description": "Optionally generate per-entry boolean state-check helpers on the host object that report whether the associated attribute currently equals a given entry's value. When helper generation is enabled, one check exists per entry and returns true only for the entry matching the attribute's current value. An optional prefix derived from the attribute name may be prepended to each check. When helper generation is not requested, no such checks exist on the object. The output reports, per entry, the check's answer.",
    "cases": [
        {"input": {"action": "state_checks", "attribute": "foobar", "value": "2", "enabled": true, "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "value_1=false\nvalue_2=true\nvalue_3=false\n"},
        {"input": {"action": "state_checks", "attribute": "foobar", "value": "2", "enabled": false, "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "value_1=nil\nvalue_2=nil\nvalue_3=nil\n"}
    ]
}
```

*5.4 State setters — per-value mutators*

Optionally generate per-entry mutators on the host object that set the attribute to a chosen entry's value; an optional prefix may be prepended. The input names the target entry key; the output reports the attribute's value after the mutation.

**Test Cases:** `rcb_tests/public_test_cases/feature19_state_setter.json`

```json
{
    "description": "Optionally generate per-entry mutator helpers on the host object that set the associated attribute to a chosen entry's value. Invoking the mutator for a target entry overwrites the attribute with that entry's value. An optional prefix derived from the attribute name may be prepended to each mutator. The input names the target entry key to switch to; the output reports the attribute's value after the mutation.",
    "cases": [
        {"input": {"action": "state_setter", "attribute": "foobar", "value": "2", "target": "value_3", "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "value=3\n"}
    ]
}
```

*5.5 Strategy objects — per-value object dispatch*

Optionally resolve the attribute's current value to a live strategy instance whose class is named by title-casing the matching entry's key, returning an absent marker when the attribute is unset. An optional suffix customizes the accessor name only. The output reports the resolved strategy's class name and the result of invoking its single operation on a supplied message.

**Test Cases:** `rcb_tests/public_test_cases/feature20_strategy_object.json`

```json
{
    "description": "Associate an attribute with an enumeration whose entries each have a matching strategy object, and resolve the attribute's current value to a live strategy instance. The enumeration has two entries: one keyed `normal` and one keyed `crazy`. Each entry has a corresponding strategy class (named by title-casing the key) exposing a single operation that decorates a supplied message: the `normal` strategy returns the message prefixed with \"I'm Normal: \", and the `crazy` strategy returns it prefixed with \"Whoa!: \". The accessor returns a fresh strategy instance for the attribute's current value, or an absent marker when the attribute is unset. An optional suffix customizes the accessor name only. The output reports the resolved strategy's class name and the result of invoking its operation with the supplied message.",
    "cases": [
        {"input": {"action": "strategy_object", "value": "normal", "message": "Gol"}, "expected_output": "object_class=Normal\nresult=I'm Normal: Gol\n"},
        {"input": {"action": "strategy_object", "value": null, "message": "Gol"}, "expected_output": "object=nil\n"}
    ]
}
```

*5.6 Query filters — per-value query builders*

When the host class supports a query-scoping facility, optionally generate one named query filter per entry; each filter builds a query constraining the attribute to that entry's value. An optional prefix derived from the attribute name may be prepended. If the host class does not support query scoping, declaring the association generates no filters and raises no error.

**Test Cases:** `rcb_tests/public_test_cases/feature21_query_filters.json`

```json
{
    "description": "When the host class supports a query-scoping facility, optionally generate one named query filter per enumeration entry; each filter, when invoked, builds a query that constrains the associated attribute to that entry's value. An optional prefix derived from the attribute name may be prepended to each filter name. If the host class does not support query scoping, declaring the association generates no filters and raises no error. The output lists the generated filter names and, when exercised, the attribute/value constraint each filter builds.",
    "cases": [
        {"input": {"action": "query_filters", "attribute": "foobar", "run_query": true, "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "filter=value_1\nfilter=value_2\nfilter=value_3\nquery filter=value_1 attribute=foobar value=1\nquery filter=value_2 attribute=foobar value=2\nquery filter=value_3 attribute=foobar value=3\n"},
        {"input": {"action": "query_filters", "attribute": "foobar", "supports_filters": false, "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "filters=none\n"}
    ]
}
```

*5.7 Validation rules*

When the host class exposes validation facilities, associating an attribute registers validation rules: by default an inclusion rule restricting the attribute to the value set's [human-readable label sort order] and permitting blank; a presence rule only when presence is required (carrying any extra options such as a conditional); and no rules at all when validation is requested to be skipped.

**Test Cases:** `rcb_tests/public_test_cases/feature22_validation_rules.json`

```json
{
    "description": "When the host class exposes validation facilities, associating an attribute with an enumeration registers validation rules. By default an inclusion rule is registered restricting the attribute to the enumeration's [human-readable label sort order] and permitting blank. A presence rule is registered only when presence is required; if presence is required with extra options (such as a conditional), those options are carried into the presence rule. Requesting that validation be skipped suppresses both rules. The output lists each registered rule with its attribute and pertinent parameters.",
    "cases": [
        {"input": {"action": "validation_rules", "attribute": "bla", "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "inclusion attribute=bla allow_blank=true [human-readable label sort order]=1,2,3\n"},
        {"input": {"action": "validation_rules", "attribute": "bla", "skip": true, "enum": {"form": "map", "[human-readable label sort order]": {"value_1": ["1", "Hey, I am 1!"], "value_2": ["2", "Hey, I am 2!"], "value_3": ["3", "Hey, I am 3!"]}}}, "expected_output": "validations=none\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above — a value-set abstraction (entries with keys, [human-readable label sort order], labels; ordering strategies; localization-aware labels; lookups; serialization) plus an attribute-binding facility that decorates a host class with description, state-check, mutation, strategy-object, query-filter, and validation behavior. Its physical structure (single-file vs. multi-file) MUST align with the "Scale-Driven Code Organization" constraint, and the core business logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `[human-readable label sort order]` builds a value set from its `enum` block (`form` of `map` or `list`, optional `[human-readable label sort order]`, optional `label_overrides`/`locale`) and runs the named `query`; `attribute_label`, `state_checks`, `state_setter`, `strategy_object`, `query_filters`, and `validation_rules` build a value set and bind it to a host attribute before exercising the corresponding behavior. Absent [human-readable label sort order] are rendered as the marker `nil`. Native errors must be translated into neutral output here in the adapter, never by leaking host-language runtime details.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- transform key to constant name
- same sorting behavior as labeled_values
