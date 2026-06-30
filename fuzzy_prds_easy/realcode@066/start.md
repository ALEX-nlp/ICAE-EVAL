## Product Requirement Document

# In-Memory Full-Text Search Engine — Text Processing, Indexing & Querying

## Project Goal

Build a lightweight, in-memory full-text search library that lets developers index plain objects and run relevance-ranked text queries against them, without standing up an external search service or database. The library covers the whole path from raw text to query results: a configurable text-processing pipeline, an inverted index keyed by processed terms, exact-match search with field selection, prefix-based autocomplete, and the small ranking primitives that support them.

---

## Background & Problem

Applications frequently need to search over a modest collection of in-memory objects (catalog entries, sentences, records) and show the best matches first. Without a dedicated library, developers re-implement the same machinery every time: normalizing text (lower-casing, stripping punctuation, splitting into tokens, stemming), building an index from object fields, deciding which fields are searchable, and scoring results. This boilerplate is repetitive and easy to get subtly wrong.

This library packages that machinery behind a small, composable interface. Text flows through an ordered pipeline of transforms; documents are reduced to an integer identifier plus their searchable text fields; queries are processed the same way as the indexed text so they match consistently; and results come back ordered by relevance. Fields can be opted out of indexing, and searches can be narrowed to specific fields.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., text transforms, the index data structure, ranking, the query model), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The text-processing pipeline must be open for extension (new transforms) but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive (a transform is a single function from a list of strings to a list of strings).
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Text Processing Transforms

**As a developer**, I want a set of single-purpose text transforms, so I can normalize text consistently before indexing or searching.

**Expected Behavior / Usage:**

Each transform takes text and returns transformed text. The execution adapter exposes one transform per request `op`. These transforms are the building blocks composed by the pipeline in Feature 2.

*1.1 Lower-casing — convert text to lower case*

Request `op` is `lowercase`. It accepts either a single `text` value or a list under `texts`. Every alphabetic character is converted to its lower-case form; digits, punctuation, apostrophes and whitespace are preserved exactly. With `texts`, each element is lower-cased independently and order is preserved; each result is printed on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_lowercase.json`

```json
{
    "description": "Lower-case text. The transform accepts either a single text value or a list of text values and returns the same shape with every alphabetic character converted to its lower-case form. Non-alphabetic characters (digits, punctuation, whitespace, apostrophes) are preserved exactly. When a list is supplied, each element is lower-cased independently and the order is preserved.",
    "cases": [
        {
            "input": {"op": "lowercase", "text": "No Toto I don't access my emails during a race"},
            "expected_output": "no toto i don't access my emails during a race\n"
        },
        {
            "input": {"op": "lowercase", "texts": ["No Michael no! This is not right", "Toto, it's called a motor race", "Sorry?", "It's called car racing"]},
            "expected_output": "no michael no! this is not right\ntoto, it's called a motor race\nsorry?\nit's called car racing\n"
        }
    ]
}
```

*1.2 Punctuation removal — strip punctuation symbols*

Request `op` is `strip_punctuation` with a single `text`. It deletes punctuation characters (commas, periods, colons, semicolons, hyphens, quotation marks, apostrophes, exclamation marks, question marks, parentheses) and leaves all other characters and inter-word whitespace untouched.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_strip_punctuation.json`

```json
{
    "description": "Remove punctuation symbols from a single text value. The transform deletes punctuation characters (such as commas, periods, colons, semicolons, hyphens, quotation marks, apostrophes, exclamation marks, question marks, and parentheses) from the text, leaving the remaining characters and the whitespace between words untouched. No characters other than the recognised punctuation are removed.",
    "cases": [
        {
            "input": {"op": "strip_punctuation", "text": "Michael, have you got a minute?"},
            "expected_output": "Michael have you got a minute\n"
        }
    ]
}
```

*1.3 Tokenization — split on whitespace*

Request `op` is `tokenize` with a single `text`. It splits the input on runs of whitespace and emits the tokens in order, one per line. Punctuation attached to a word stays part of that token; only whitespace separates tokens.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_tokenize.json`

```json
{
    "description": "Split a text value into tokens on whitespace. The transform breaks the input on runs of whitespace and returns the resulting tokens in order. Punctuation that is attached to a word is kept as part of that token; only whitespace acts as a separator.",
    "cases": [
        {
            "input": {"op": "tokenize", "text": "Valtteri, it's James"},
            "expected_output": "Valtteri,\nit's\nJames\n"
        }
    ]
}
```

*1.4 Stemming — reduce a word to its Porter stem*

Request `op` is `stem` with a single `text`. It applies the Porter stemming algorithm so that inflected forms of a root word reduce to a common stem; the stem of an already-reduced word is the word itself.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_stemming.json`

```json
{
    "description": "Reduce a word to its stem using the Porter stemming algorithm. Inflected forms of the same root word are reduced to a common stem, so that, for example, a plural or otherwise inflected form and its base form collapse to the same string. The stem of an already-reduced word is the word itself.",
    "cases": [
        {"input": {"op": "stem", "text": "moves"}, "expected_output": "move\n"},
        {"input": {"op": "stem", "text": "move"}, "expected_output": "move\n"}
    ]
}
```

---

### Feature 2: Composable Processing Pipeline

**As a developer**, I want to chain transforms into a single pipeline, so I can normalize text in one configurable pass and reuse the same rules for indexing and querying.

**Expected Behavior / Usage:**

Request `op` is `pipeline` with an ordered `steps` array (step names drawn from `lowercase`, `strip_punctuation`, `tokenize`, `stem`) and a `text`. The pipeline feeds the input through each step in order, passing each step's output as the next step's input, and emits the final tokens one per line.

*2.1 Empty pipeline — pass text through unchanged*

When `steps` is empty, the pipeline performs no transformation and returns the original input as a single token.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_empty_pipeline.json`

```json
{
    "description": "Run text through a processing pipeline that has no steps configured. An empty pipeline performs no transformation: it returns the original input text unchanged as a single token, exactly as it was supplied.",
    "cases": [
        {"input": {"op": "pipeline", "steps": [], "text": "El plan is working"}, "expected_output": "El plan is working\n"}
    ]
}
```

*2.2 Multi-step pipeline — chain several transforms*

When `steps` lists several transforms, the output of each becomes the input of the next. For example, lower-casing then stripping punctuation then tokenizing yields cleaned, lower-cased tokens in order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_pipeline_steps.json`

```json
{
    "description": "Run text through a processing pipeline composed of an ordered list of named steps. Each step's output becomes the next step's input. Here the pipeline lower-cases the text, removes punctuation, and then splits on whitespace, producing a list of cleaned tokens in order. The available step names are lowercase, strip_punctuation, tokenize, and stem.",
    "cases": [
        {"input": {"op": "pipeline", "steps": ["lowercase", "strip_punctuation", "tokenize"], "text": "El plan is working!"}, "expected_output": "el\nplan\nis\nworking\n"}
    ]
}
```

---

### Feature 3: Approximate String Matching (Edit Distance)

**As a developer**, I want to measure how different two strings are, so I can rank near-matches (this metric underpins autocomplete ranking).

**Expected Behavior / Usage:**

Request `op` is `levenshtein` with two strings `a` and `b`. It returns the Levenshtein edit distance: the minimum number of single-character insertions, deletions, or substitutions (each costing one) needed to transform one string into the other. Two empty or two identical strings give zero; if exactly one string is empty, the distance equals the length of the other. The result is printed as a single integer.

**Test Cases:** `rcb_tests/public_test_cases/feature3_edit_distance.json`

```json
{
    "description": "Compute the edit (Levenshtein) distance between two strings: the minimum number of single-character insertions, deletions, or substitutions needed to turn one string into the other, with each operation costing one. Two empty strings or two identical strings have distance zero; when one string is empty the distance equals the length of the other.",
    "cases": [
        {"input": {"op": "levenshtein", "a": "", "b": ""}, "expected_output": "0\n"},
        {"input": {"op": "levenshtein", "a": "ephrem", "b": "benyam"}, "expected_output": "5\n"}
    ]
}
```

---

### Feature 4: In-Memory Full-Text Search Index

**As a developer**, I want to add documents to an index and query them, so I can find the documents whose text matches a query.

**Expected Behavior / Usage:**

The index is driven by a request with `op` `index` and an ordered `actions` array. Each action mutates or queries the index and may emit one output line. A document is an object carrying an integer identifier field plus one or more text fields; document text is indexed after passing through the default pipeline (lower-case, strip punctuation, tokenize, Porter stem), and queries are processed the same way so they match consistently. The supported actions are: `add` (insert a document), `remove` (delete a document), `size` (current document count), `docs` (sorted identifiers held), `search` (relevance query, optionally restricted to named fields via `select`), and `autocomplete` (prefix suggestions).

*4.1 Document count, de-duplication & identifier listing*

`add` increases the document count by one. Adding a document whose identifier already exists is ignored (no duplicate). `size` emits `size=<count>`; `docs` emits `docs=<[numeric format for doc list separation] sorted identifiers>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_index_size.json`

```json
{
    "description": "Build an in-memory index and observe how many documents it holds. A document has an integer identifier field plus one or more text fields. Adding a document increases the document count by one; adding a document whose identifier is already present leaves the count unchanged (no duplicate). The index can also report the sorted list of identifiers it currently holds. Each action emits one line: 'size=<count>' or 'docs=<[numeric format for doc list separation] sorted identifiers>'.",
    "cases": [
        {
            "input": {"op": "index", "actions": [
                {"action": "size"},
                {"action": "add", "doc": {"type": "book", "id": 0, "title": "How to Build a Car", "author": "Adrian Newey", "publisher": "HarperCollins"}},
                {"action": "size"},
                {"action": "add", "doc": {"type": "book", "id": 0, "title": "How to Build a Car", "author": "Adrian Newey", "publisher": "HarperCollins"}},
                {"action": "size"},
                {"action": "docs"}
            ]},
            "expected_output": "size=0\nsize=1\nsize=1\ndocs=0\n"
        }
    ]
}
```

*4.2 Removing documents*

`remove` deletes the document with the given identifier and lowers the count. Removing an identifier that is not present is a safe no-op (no error, count unchanged).

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_remove.json`

```json
{
    "description": "Remove a previously added document from the index, identified by its identifier. After removal the document count drops accordingly. Removing a document whose identifier is not present in the index is a safe no-op that does not raise an error and leaves the count unchanged. Each 'size' action emits one line 'size=<count>'.",
    "cases": [
        {
            "input": {"op": "index", "actions": [
                {"action": "add", "doc": {"type": "sentence", "line": 0, "value": "the quick brown fox"}},
                {"action": "size"},
                {"action": "remove", "doc": {"type": "sentence", "line": 0, "value": "the quick brown fox"}},
                {"action": "size"},
                {"action": "remove", "doc": {"type": "sentence", "line": 9, "value": "not present"}},
                {"action": "size"}
            ]},
            "expected_output": "size=1\nsize=0\nsize=0\n"
        }
    ]
}
```

*4.3 Searching for matching documents*

`search` processes the `query` through the default pipeline and returns every document whose indexed text contains a resulting term. A term present in several documents returns all of them; a query with no matches returns nothing. Output is one line `search=<[numeric format for doc list separation] entries sorted by document identifier>`, where each entry is `<documentId>:<matchTerm>` and `matchTerm` is the processed (stemmed) query term that matched.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_search.json`

```json
{
    "description": "Search the index for documents matching a query. The query is run through the default text pipeline (lower-casing, punctuation removal, whitespace tokenization, and Porter stemming), and any document whose indexed text contains a resulting term is returned. A term that appears in several documents returns all of them. A query with no matches returns an empty result. Each search emits one line 'search=<[numeric format for doc list separation] entries sorted by document identifier>' where each entry is '<documentId>:<matchTerm>' and matchTerm is the processed (stemmed) query term that matched.",
    "cases": [
        {
            "input": {"op": "index", "actions": [
                {"action": "add", "doc": {"type": "book", "id": 0, "title": "Pride and Prejudice", "author": "Jane Austen", "publisher": "P"}},
                {"action": "add", "doc": {"type": "book", "id": 1, "title": "Sense and Sensibility", "author": "Jane Austen", "publisher": "P"}},
                {"action": "add", "doc": {"type": "book", "id": 2, "title": "Moby Dick", "author": "Herman Melville", "publisher": "P"}},
                {"action": "search", "query": "austen"},
                {"action": "search", "query": "melville"},
                {"action": "search", "query": "nonexistentword"}
            ]},
            "expected_output": "search=0:austen,1:austen\nsearch=2:melvil\nsearch=\n"
        }
    ]
}
```

*4.4 Fields excluded from indexing*

A document may mark some fields as excluded from indexing. Text appearing only in an excluded field is never indexed, so searching for it returns nothing, while text in ordinary indexed fields of the same document is still found.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_ignored_fields.json`

```json
{
    "description": "Fields of a document may be marked to be excluded from indexing. The text of an excluded field is never added to the index, so searching for words that appear only in an excluded field returns no results, while words in ordinary (indexed) text fields of the same document are still found. Each search emits one line 'search=<[numeric format for doc list separation] documentId:matchTerm entries>' (empty after the '=' when there are no matches).",
    "cases": [
        {
            "input": {"op": "index", "actions": [
                {"action": "add", "doc": {"type": "book", "id": 0, "title": "How to Build a Car", "author": "Adrian Newey", "publisher": "Harpercollins"}},
                {"action": "search", "query": "harpercollins"},
                {"action": "search", "query": "newey"}
            ]},
            "expected_output": "search=\nsearch=0:newei\n"
        }
    ]
}
```

*4.5 Restricting search to selected fields*

A `search` may carry a `select` list naming the fields to consider. With no `select` key, all indexed fields are searched. When specific fields are named, only matches inside those fields count, so a term present only in an unselected field yields nothing. An explicitly empty `select` list selects nothing and returns no results. Selecting a field that is excluded from indexing, or a name that is not a field of the document, also returns nothing.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_select_props.json`

```json
{
    "description": "A search may restrict matching to a chosen subset of document fields by naming them in a 'select' list. With no 'select' key, all indexed fields are searched. When 'select' names specific field(s), only matches found within those fields count, so a term present only in an unselected field yields no results. An explicitly empty 'select' list selects nothing and therefore returns no results. Selecting a field that is excluded from indexing, or a field name that does not belong to the document, also returns no results. Each search emits one line 'search=<[numeric format for doc list separation] documentId:matchTerm entries>' (empty after '=' when there are no matches).",
    "cases": [
        {
            "input": {"op": "index", "actions": [
                {"action": "add", "doc": {"type": "book", "id": 0, "title": "Atomic Habits", "author": "James Clear", "publisher": "Penguin"}},
                {"action": "search", "query": "atomic"},
                {"action": "search", "query": "clear"},
                {"action": "search", "query": "atomic", "select": ["title"]},
                {"action": "search", "query": "clear", "select": ["title"]},
                {"action": "search", "query": "atomic", "select": []},
                {"action": "search", "query": "penguin", "select": ["publisher"]},
                {"action": "search", "query": "atomic", "select": ["value"]}
            ]},
            "expected_output": "search=0:atom\nsearch=0:clear\nsearch=0:atom\nsearch=\nsearch=\nsearch=\nsearch=\n"
        }
    ]
}
```

*4.6 Autocomplete suggestions*

`autocomplete` returns every indexed term that begins with the given prefix, ordered by a relevance score; an empty list results when nothing matches (including an empty index). Output is one line `autocomplete=<[numeric format for doc list separation] suggestions in relevance order>`. Because indexed terms are stored in stemmed form, suggestions reflect stems rather than the original words.

**Test Cases:** `rcb_tests/public_test_cases/feature4_6_autocomplete.json`

```json
{
    "description": "Fetch autocomplete suggestions for a query prefix. The index returns every indexed term that begins with the given prefix, ordered by a relevance score. When no indexed term starts with the prefix (including an empty index), the suggestion list is empty. Each action emits one line 'autocomplete=<[numeric format for doc list separation] suggestions in relevance order>' (empty after '=' when there are none). Note that indexed terms are stored in their stemmed form, so suggestions reflect stems rather than original words.",
    "cases": [
        {
            "input": {"op": "index", "actions": [
                {"action": "add", "doc": {"type": "sentence", "line": 0, "value": "football"}},
                {"action": "add", "doc": {"type": "sentence", "line": 1, "value": "foil"}},
                {"action": "autocomplete", "query": "fo"}
            ]},
            "expected_output": "autocomplete=footbal,foil\n"
        },
        {
            "input": {"op": "index", "actions": [
                {"action": "autocomplete", "query": "foo"}
            ]},
            "expected_output": "autocomplete=\n"
        }
    ]
}
```

*4.7 Document identifier validation*

Every document must carry exactly one integer identifier. Adding a document that violates this is rejected (not indexed) and reported as a neutral, language-independent error category: a document with no identifier field reports `missing_id`; an identifier field that is not an integer reports `invalid_id_type`; a document declaring more than one identifier field reports `multiple_ids`. Each rejected add emits one line `error=<category>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_7_identifier_validation.json`

```json
{
    "description": "Every document added to the index must carry exactly one integer identifier. Adding a document that violates this rule is rejected and reported as a neutral, language-independent error category instead of being indexed: a document with no identifier field reports 'missing_id'; a document whose identifier field is not an integer reports 'invalid_id_type'; a document declaring more than one identifier field reports 'multiple_ids'. Each rejected add emits one line 'error=<category>'.",
    "cases": [
        {"input": {"op": "index", "actions": [{"action": "add", "doc": {"type": "no_id", "title": "Test"}}]}, "expected_output": "error=missing_id\n"},
        {"input": {"op": "index", "actions": [{"action": "add", "doc": {"type": "string_id", "id": "abc", "title": "Test"}}]}, "expected_output": "error=invalid_id_type\n"},
        {"input": {"op": "index", "actions": [{"action": "add", "doc": {"type": "two_id", "a": 1, "b": 2}}]}, "expected_output": "error=multiple_ids\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — text transforms, a composable processing pipeline, an in-memory inverted index with add/remove/search/autocomplete, field selection and exclusion, and the edit-distance primitive. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint, and the core logic MUST be decoupled from stdin/stdout and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to the core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, dispatches on the `op` field (`lowercase`, `strip_punctuation`, `tokenize`, `stem`, `pipeline`, `levenshtein`, `index`), invokes the appropriate core logic, and prints the result to stdout matching the per-feature contracts above. For `index`, it walks the `actions` array in order; documents are supplied inline with a `type` discriminator and field values, including the cases needed to exercise identifier validation (no identifier, non-integer identifier, multiple identifiers). Native exceptions raised by the core must be translated into the neutral `error=<category>` lines specified in Feature 4.7 — this translation happens in the adapter's render layer, never by altering core logic.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same ordering convention as the header module
