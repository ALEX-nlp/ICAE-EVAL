## Product Requirement Document

# Text Classification and Semantic Indexing Toolkit - Input/Output Contract

## Project Goal

Build a text classification and semantic indexing toolkit that allows developers to tokenize text, train supervised classifiers, rank related documents, search semantic indexes, and summarize content without hand-writing repetitive text normalization, scoring, and ranking logic.

---

## Background & Problem

Without this library/tool, developers are forced to manually split text into useful terms, remove stopwords, maintain category statistics, compute document relationships, and format ranked results. This leads to repetitive code, inconsistent scoring behavior, and fragile handling of edge cases such as empty vectors, all-stopword documents, unknown categories, and persisted indexes.

With this library/tool, developers can provide plain text, labels, vectors, matrices, and document collections and receive deterministic stdout contracts that expose the externally visible behavior of normalization, probabilistic classification, semantic indexing, search, summarization, and validation.

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

### Feature 1: Token Frequency Extraction

**As a developer**, I want to turn text into repeatable term counts, so I can inspect the normalized vocabulary that will drive classification.

**Expected Behavior / Usage:**

The input is a JSON object containing text, a stopword language, whether punctuation tokens are retained, and whether stemming is enabled. The output is one `token=count` line per retained token, sorted lexically by token text. Stopwords are removed when punctuation filtering is disabled; stemming collapses inflected words to their root form when enabled.

**Test Cases:** `rcb_tests/public_test_cases/feature1_token_frequency.json`

```json
{
    "description": "Counts meaningful terms in text after configurable punctuation filtering, stopword removal, and optional stemming.",
    "cases": [
        {
            "input": {
                "text": "here are some good words of test's. I hope you love them!",
                "include_punctuation": true,
                "stopword_language": "en",
                "stem": true
            },
            "expected_output": "!=1\n'=1\n.=1\ngood=1\nhope=1\nlove=1\ntest=1\nthem=1\nword=1\n"
        },
        {
            "input": {
                "text": "here are some good words of test's. I hope you love them!",
                "include_punctuation": false,
                "stopword_language": "en",
                "stem": true
            },
            "expected_output": "good=1\nhope=1\nlove=1\ntest=1\nthem=1\nword=1\n"
        },
        {
            "input": {
                "text": "here are some good words of test's. I hope you love them!",
                "include_punctuation": false,
                "stopword_language": "en",
                "stem": false
            },
            "expected_output": "good=1\nhope=1\nlove=1\ntests=1\nthem=1\nwords=1\n"
        }
    ]
}
```

---

### Feature 2: Zero Vector Detection

**As a developer**, I want to check whether numeric vectors contain no nonzero values, so I can safely handle empty vectors and all-zero vectors in downstream numeric processing.

**Expected Behavior / Usage:**

The input is a JSON object with an array of numeric vectors. Each vector is an array of numbers and may be empty. The output reports each vector length and whether it is a zero vector using `yes` or `no`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_zero_vector_detection.json`

```json
{
    "description": "Reports whether numeric vectors are zero vectors, including empty vectors and vectors containing only zero values.",
    "cases": [
        {
            "input": {
                "vectors": [
                    [],
                    [
                        0
                    ],
                    [
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0
                    ]
                ]
            },
            "expected_output": "vector_0_length=0\nvector_0_zero=yes\nvector_1_length=1\n[a specific magic constant configuration for zero vectors]\nvector_2_length=10\n[a specific magic constant configuration for zero vectors]\n"
        }
    ]
}
```

---

### Feature 3: Matrix Singular Decomposition

**As a developer**, I want to decompose numeric matrices into singular-value components, so I can validate numeric preprocessing without failing on identity-like matrices.

**Expected Behavior / Usage:**

The input is a rectangular numeric matrix. The output reports input dimensions, decomposition matrix dimensions, and comma-separated singular values rounded to two decimals.

**Test Cases:** `rcb_tests/public_test_cases/feature3_matrix_singular_decomposition.json`

```json
{
    "description": "Decomposes a numeric matrix and reports the dimensions of decomposition outputs plus rounded singular values.",
    "cases": [
        {
            "input": {
                "matrix": [
                    [
                        1,
                        0
                    ],
                    [
                        0,
                        1
                    ]
                ]
            },
            "expected_output": "input_rows=2\ninput_columns=2\nleft_rows=2\nleft_columns=2\nright_rows=2\nright_columns=2\nsingular_values=1.00,1.00\n"
        }
    ]
}
```

---

### Feature 4: Ordered Unique Vocabulary

**As a developer**, I want to build a vocabulary that preserves first-seen word order, so I can map words to stable positions and retrieve words by position.

**Expected Behavior / Usage:**

The input contains a sequence of words to add, words to look up, and numeric positions to read back. Adding a duplicate word must not increase vocabulary size. The output reports size after each addition, position for each lookup word, and word at each requested index.

**Test Cases:** `rcb_tests/public_test_cases/feature4_ordered_word_vocabulary.json`

```json
{
    "description": "Maintains an ordered unique vocabulary where duplicate additions do not increase size and positions follow first insertion order.",
    "cases": [
        {
            "input": {
                "words": [
                    "hello",
                    "hello",
                    "world"
                ],
                "lookups": [
                    "hello",
                    "world"
                ],
                "indexes": [
                    0,
                    1
                ]
            },
            "expected_output": "size_after_0=1\nsize_after_1=1\nsize_after_2=2\nposition_hello=0\nposition_world=1\nword_at_0=hello\nword_at_1=world\n"
        }
    ]
}
```

---

### Feature 5.1: Probabilistic Training and Categories

**As a developer**, I want to train a supervised text classifier and inspect category state, so I can confirm accepted terms and available categories before classification.

**Expected Behavior / Usage:**

The input declares starting categories, labeled training samples, and optionally a category to add. The output reports whether stemming is enabled, the initial category list, the retained training tokens for each sample, and the final sorted category list.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_probabilistic_training_categories.json`

```json
{
    "description": "Trains a probabilistic text classifier, returns accepted training tokens, and reports category state before and after adding a category.",
    "cases": [
        {
            "input": {
                "initial_categories": [
                    "Interesting",
                    "Uninteresting"
                ],
                "training": [
                    {
                        "category": "Interesting",
                        "text": "love"
                    },
                    {
                        "category": "Interesting",
                        "text": "Água"
                    }
                ],
                "add_category": "Test"
            },
            "expected_output": "stemmer=enabled\ninitial_categories=Interesting,Uninteresting\ntrained_Interesting=love\ntrained_Interesting=Água\nfinal_categories=Interesting,Test,Uninteresting\n"
        }
    ]
}
```

---

### Feature 5.2: Dynamic Category Handling

**As a developer**, I want to control whether previously unseen labels are accepted during training, so I can choose between strict category validation and automatic label creation.

**Expected Behavior / Usage:**

The input declares initial categories, a dynamic-category flag, and one labeled training sample whose label may be new. When dynamic categories are enabled, the output reports the expanded category list and count. When they are disabled, the output uses a normalized error contract with `error=category_not_found` and the rejected category.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_dynamic_category_handling.json`

```json
{
    "description": "Handles training for categories that were not declared at creation time according to the configured dynamic-category policy.",
    "cases": [
        {
            "input": {
                "initial_categories": [
                    "Interesting",
                    "Uninteresting"
                ],
                "auto_categorize": true,
                "training": {
                    "category": "Ruby",
                    "text": "A really sweet language"
                }
            },
            "expected_output": "categories=Interesting,Ruby,Uninteresting\ncategory_count=3\n"
        },
        {
            "input": {
                "initial_categories": [
                    "Interesting",
                    "Uninteresting"
                ],
                "auto_categorize": false,
                "training": {
                    "category": "Ruby",
                    "text": "A really sweet language"
                }
            },
            "expected_output": "error=category_not_found\ncategory=Ruby\n"
        }
    ]
}
```

---

### Feature 5.3: Probabilistic Classification Scores

**As a developer**, I want to classify trained text with a numeric score, so I can compare the winning label and confidence signal for a query.

**Expected Behavior / Usage:**

The input contains category names, labeled training samples, and query texts. The output reports the predicted category and rounded score for each query as separate lines.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_probabilistic_classification.json`

```json
{
    "description": "Classifies text after supervised training and exposes both predicted category and rounded numeric confidence score.",
    "cases": [
        {
            "input": {
                "categories": [
                    "Interesting",
                    "Uninteresting"
                ],
                "training": [
                    {
                        "category": "Interesting",
                        "text": "here are some good words. I hope you love them"
                    },
                    {
                        "category": "Uninteresting",
                        "text": "here are some bad words, I hate you"
                    }
                ],
                "queries": [
                    "I hate bad words and you"
                ]
            },
            "expected_output": "query_0_category=Uninteresting\nquery_0_score=-4.85\n"
        }
    ]
}
```

---

### Feature 5.4: Thresholded Classification

**As a developer**, I want to reject out-of-distribution inputs below a configured confidence threshold, so I can avoid returning weak classifications for unfamiliar text.

**Expected Behavior / Usage:**

The input contains one category, a threshold, training terms, a training repeat count, and queries. Training terms repeated enough should classify to the category; unrelated queries that do not meet the threshold output `none`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_threshold_classification.json`

```json
{
    "description": "Applies an enabled confidence threshold so familiar inputs classify to the trained category and out-of-distribution inputs return no category.",
    "cases": [
        {
            "input": {
                "category": "Number",
                "threshold": -4.0,
                "training_terms": [
                    "one",
                    "two",
                    "three",
                    "four",
                    "five"
                ],
                "repeat": 2,
                "queries": [
                    "one",
                    "two",
                    "three",
                    "four",
                    "five",
                    "xyzzy"
                ]
            },
            "expected_output": "one=Number\ntwo=Number\nthree=Number\nfour=Number\nfive=Number\nxyzzy=none\n"
        }
    ]
}
```

---

### Feature 5.5: Untraining Effects

**As a developer**, I want to remove learned evidence from a category, so I can change later predictions when prior evidence is withdrawn.

**Expected Behavior / Usage:**

The input contains categories, training samples, untraining samples, and a query. The output reports the query prediction before and after untraining so the effect is externally visible.

**Test Cases:** `rcb_tests/public_test_cases/feature5_5_untraining_changes_predictions.json`

```json
{
    "description": "Removes previously learned evidence and reports that the prediction for an affected query changes after untraining.",
    "cases": [
        {
            "input": {
                "categories": [
                    "Interesting",
                    "Uninteresting",
                    "colors"
                ],
                "training": [
                    {
                        "category": "Interesting",
                        "text": "here are some good words. I hope you love them"
                    },
                    {
                        "category": "Uninteresting",
                        "text": "here are some bad words, I hate you"
                    },
                    {
                        "category": "colors",
                        "text": "red orange green blue seven"
                    }
                ],
                "untraining": [
                    {
                        "category": "colors",
                        "text": "seven"
                    }
                ],
                "query": "seven"
            },
            "expected_output": "before=Colors\nafter=Uninteresting\n"
        }
    ]
}
```

---

### Feature 5.6: Custom Stopwords

**As a developer**, I want to configure stopwords supplied by the caller, so I can ignore caller-defined uninformative text while still training on useful text.

**Expected Behavior / Usage:**

The input supplies custom stopwords, labeled training samples, and queries. All-stopword training text must not create useful evidence, while later non-stopword text may create a category. Query output reports predicted category and rounded score, using `infinity` for a query that has no usable evidence.

**Test Cases:** `rcb_tests/public_test_cases/feature5_6_custom_stopwords.json`

```json
{
    "description": "Uses caller-supplied stopwords to skip all-stopword training text while allowing other text to train and affect classification scores.",
    "cases": [
        {
            "input": {
                "stopwords": [
                    "these",
                    "are",
                    "custom",
                    "stopwords"
                ],
                "training": [
                    {
                        "category": "Stopwords",
                        "text": "Custom stopwords"
                    },
                    {
                        "category": "Stopwords",
                        "text": "To be or not to be"
                    }
                ],
                "queries": [
                    "These stopwords",
                    "To be or not to be"
                ]
            },
            "expected_output": "categories=Stopwords\nquery_0_category=Stopwords\nquery_0_score=infinity\nquery_1_category=Stopwords\nquery_1_score=0.00\n"
        }
    ]
}
```

---

### Feature 6.1: Semantic Related Documents

**As a developer**, I want to find documents semantically related to a query document, so I can rank related content beyond literal text equality.

**Expected Behavior / Usage:**

The input contains documents, a query document, and a result limit. The output lists ranked related documents as `rank_N=<document>` lines in descending relatedness order.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_semantic_related_documents.json`

```json
{
    "description": "Indexes documents semantically and returns the most related documents for a query in ranked order.",
    "cases": [
        {
            "input": {
                "documents": [
                    "This text deals with dogs. Dogs.",
                    "This text involves dogs too. Dogs! ",
                    "This text revolves around cats. Cats.",
                    "This text also involves cats. Cats!",
                    "This text involves birds. Birds."
                ],
                "query": "This text deals with dogs. Dogs.",
                "limit": 3
            },
            "expected_output": "rank_0=This text involves dogs too. Dogs! \nrank_1=This text involves birds. Birds.\nrank_2=This text revolves around cats. Cats.\n"
        }
    ]
}
```

---

### Feature 6.2: Semantic Classification Scores

**As a developer**, I want to assign categories using a semantic document index, so I can classify content by latent relationships and inspect scores.

**Expected Behavior / Usage:**

The input contains labeled documents and query documents. The output reports a predicted category and rounded semantic score for each query.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_semantic_classification_scores.json`

```json
{
    "description": "Assigns semantic categories to query documents and reports rounded scores for each classification.",
    "cases": [
        {
            "input": {
                "training": [
                    {
                        "text": "This text involves dogs too. Dogs! ",
                        "category": "Dog"
                    },
                    {
                        "text": "This text revolves around cats. Cats.",
                        "category": "Cat"
                    },
                    {
                        "text": "This text also involves cats. Cats!",
                        "category": "Cat"
                    },
                    {
                        "text": "This text involves birds. Birds.",
                        "category": "Bird"
                    }
                ],
                "queries": [
                    "This text deals with dogs. Dogs.",
                    "This text revolves around cats. Cats.",
                    "This text involves birds. Birds."
                ]
            },
            "expected_output": "query_0_category=Dog\nquery_0_score=2.49\nquery_1_category=Cat\nquery_1_score=1.41\nquery_2_category=Bird\nquery_2_score=2.00\n"
        }
    ]
}
```

---

### Feature 6.3: Semantic Scored Categories

**As a developer**, I want to rank relevant categories for a mixed query, so I can see which labels have semantic evidence for the query.

**Expected Behavior / Usage:**

The input contains categorized documents and a mixed query. The output reports the number of relevant categories and each ranked category with its rounded score.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_semantic_scored_categories.json`

```json
{
    "description": "Ranks semantic categories related to a mixed query and reports only categories with relevant evidence.",
    "cases": [
        {
            "input": {
                "documents": [
                    "This text deals with dogs. Dogs.",
                    "This text involves dogs too. Dogs! ",
                    "This text revolves around cats. Cats.",
                    "This text also involves cats. Cats!",
                    "This text involves birds. Birds."
                ],
                "query": "dog bird cat"
            },
            "expected_output": "result_count=2\nrank_0=Bird:0.67\nrank_1=Dog:0.69\n"
        }
    ]
}
```

---

### Feature 6.4: Semantic Context Classification

**As a developer**, I want to compare semantic classification with token-probability classification, so I can confirm that contextual subject matter can win over literal-token similarity.

**Expected Behavior / Usage:**

The input contains shared labeled training documents and a query. The output reports the semantic classifier result and the probabilistic classifier result separately, making their externally visible disagreement explicit.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_semantic_context_classification.json`

```json
{
    "description": "Demonstrates that semantic classification can prefer contextual subject matter over a purely token-probability classifier on the same training set.",
    "cases": [
        {
            "input": {
                "categories": [
                    "Dog",
                    "Cat",
                    "Bird"
                ],
                "training": [
                    {
                        "text": "This text deals with dogs. Dogs.",
                        "category": "Dog"
                    },
                    {
                        "text": "This text involves dogs too. Dogs! ",
                        "category": "Dog"
                    },
                    {
                        "text": "This text revolves around cats. Cats.",
                        "category": "Cat"
                    },
                    {
                        "text": "This text also involves cats. Cats!",
                        "category": "Cat"
                    },
                    {
                        "text": "This text involves birds. Birds.",
                        "category": "Bird"
                    }
                ],
                "query": "This text revolves around dogs."
            },
            "expected_output": "semantic_category=Dog\nprobabilistic_category=Cat\n"
        }
    ]
}
```

---

### Feature 6.5: Semantic Recategorization

**As a developer**, I want to change labels attached to indexed documents, so I can update later semantic classifications without rebuilding the index.

**Expected Behavior / Usage:**

The input contains documents, a query, and recategorization operations identifying existing document text and replacement category. The output reports classification before the change, whether a rebuild is needed, and classification after the change.

**Test Cases:** `rcb_tests/public_test_cases/feature6_5_semantic_recategorization.json`

```json
{
    "description": "Allows categories attached to existing indexed documents to be changed without rebuilding the index, changing later classifications.",
    "cases": [
        {
            "input": {
                "documents": [
                    "This text deals with dogs. Dogs.",
                    "This text involves dogs too. Dogs! ",
                    "This text revolves around cats. Cats.",
                    "This text also involves cats. Cats!",
                    "This text involves birds. Birds."
                ],
                "query": "This text revolves around dogs.",
                "recategorize": [
                    {
                        "text": "This text deals with dogs. Dogs.",
                        "category": "Cow"
                    },
                    {
                        "text": "This text involves dogs too. Dogs! ",
                        "category": "Cow"
                    }
                ]
            },
            "expected_output": "before=Dog\nneeds_rebuild=no\nafter=Cow\n"
        }
    ]
}
```

---

### Feature 6.6: Semantic Search Ranking

**As a developer**, I want to search indexed documents by phrase or keyword, so I can retrieve ranked documents for different query shapes.

**Expected Behavior / Usage:**

The input contains documents and one or more search queries with limits. The output identifies each query and then lists ranked matching documents for that query.

**Test Cases:** `rcb_tests/public_test_cases/feature6_6_semantic_search_ranking.json`

```json
{
    "description": "Searches indexed documents by query text and returns ranked document matches for phrase and keyword queries.",
    "cases": [
        {
            "input": {
                "documents": [
                    "This text deals with dogs. Dogs.",
                    "This text involves dogs too. Dogs! ",
                    "This text revolves around cats. Cats.",
                    "This text also involves cats. Cats!",
                    "This text involves birds. Birds."
                ],
                "queries": [
                    {
                        "text": "dog involves",
                        "limit": 100
                    },
                    {
                        "text": "dog",
                        "limit": 5
                    }
                ]
            },
            "expected_output": "query_0=dog involves\nquery_0_rank_0=This text involves dogs too. Dogs! \nquery_0_rank_1=This text deals with dogs. Dogs.\nquery_0_rank_2=This text also involves cats. Cats!\nquery_0_rank_3=This text involves birds. Birds.\nquery_0_rank_4=This text revolves around cats. Cats.\nquery_1=dog\nquery_1_rank_0=This text deals with dogs. Dogs.\nquery_1_rank_1=This text involves dogs too. Dogs! \nquery_1_rank_2=This text also involves cats. Cats!\nquery_1_rank_3=This text involves birds. Birds.\nquery_1_rank_4=This text revolves around cats. Cats.\n"
        }
    ]
}
```

---

### Feature 6.7: Serialized Index Consistency

**As a developer**, I want to persist and restore a semantic index, so I can keep search behavior stable across serialization boundaries.

**Expected Behavior / Usage:**

The input contains documents, a query, and a limit. The output lists original search rankings and restored-index rankings; corresponding ranks must match.

**Test Cases:** `rcb_tests/public_test_cases/feature6_7_serialized_index_consistency.json`

```json
{
    "description": "Serializes and restores a semantic index while preserving ranked search results.",
    "cases": [
        {
            "input": {
                "documents": [
                    "This text deals with dogs. Dogs.",
                    "This text involves dogs too. Dogs! ",
                    "This text revolves around cats. Cats.",
                    "This text also involves cats. Cats!",
                    "This text involves birds. Birds."
                ],
                "query": "cat",
                "limit": 3
            },
            "expected_output": "original_rank_0=This text revolves around cats. Cats.\noriginal_rank_1=This text also involves cats. Cats!\noriginal_rank_2=This text involves dogs too. Dogs! \nrestored_rank_0=This text revolves around cats. Cats.\nrestored_rank_1=This text also involves cats. Cats!\nrestored_rank_2=This text involves dogs too. Dogs! \n"
        }
    ]
}
```

---

### Feature 6.8: Keywords and Summary

**As a developer**, I want to extract representative keyword stems and a short summary, so I can surface compact signals from longer text collections.

**Expected Behavior / Usage:**

The input contains indexed documents, one document used for keyword extraction, a summary source, and a requested sentence count. The output reports comma-separated keyword stems and the generated summary string.

**Test Cases:** `rcb_tests/public_test_cases/feature6_8_keywords_and_summary.json`

```json
{
    "description": "Extracts highest-ranked keyword stems from a document and summarizes a document collection into a fixed number of representative sentences.",
    "cases": [
        {
            "input": {
                "documents": [
                    "This text deals with dogs. Dogs.",
                    "This text involves dogs too. Dogs! ",
                    "This text revolves around cats. Cats.",
                    "This text also involves cats. Cats!",
                    "This text involves birds. Birds."
                ],
                "keyword_source": "This text deals with dogs. Dogs.",
                "summary_source": "This text deals with dogs. Dogs.This text involves dogs too. Dogs! This text revolves around cats. Cats.This text also involves cats. Cats!This text involves birds. Birds.",
                "sentence_count": 2
            },
            "expected_output": "keywords=dog,text,deal\nsummary=This text involves dogs too [...] This text also involves cats\n"
        }
    ]
}
```

---

### Feature 6.9: Document Validation Warning

**As a developer**, I want to identify documents that contain no usable terms, so I can warn callers before unusable text affects an index.

**Expected Behavior / Usage:**

The input contains one document. If the document is made only of stopwords or words too short to produce usable terms, the output reports `warning=empty_document` and echoes the raw document in a separate field; otherwise it reports `warning=none`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_9_document_validation_warning.json`

```json
{
    "description": "Warns in normalized form when an added document contains only stopwords or words too short to produce usable terms.",
    "cases": [
        {
            "input": {
                "document": "i can"
            },
            "expected_output": "warning=empty_document\ndocument=i can\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_token_frequency.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_token_frequency@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- refer to the 'headers' module for position logic
- compare with the 'semantic_related_documents' ranking style
