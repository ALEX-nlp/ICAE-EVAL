# Subjective Code Comparison

You are a senior code reviewer. Compare two source trees and write a subjective assessment. This is a STATIC review — do not run the code.

## Inputs

- **Original (reference) source**: `{ORIG_PATH}`
- **Generated source (under review)**: `{GEN_PATH}`
- **In-scope** (only review source under these paths; if empty, review the whole tree): `{IN_SCOPE_PATHS}`
- **Output**: write a single JSON file to `{OUTPUT_PATH}`

Exclude tests, build artifacts (`bin/`, `obj/`, `target/`, `vendor/`, `.gradle/`, `node_modules/`, `dist/`, etc.), generated files, and configuration when reading either tree.

## Output schema

```json
{
  "repo_id": "{REPO_ID}",
  "subjective": {
    "scope_language":              "<language of the in-scope subset>",
    "original_language":           "<primary language of the source repo>",
    "evidence_gathering": {
      "original_public_surface":   "<key public types/signatures extracted from ORIG_PATH>",
      "generated_public_surface":  "<key public types/signatures extracted from GEN_PATH>",
      "semantic_divergence_points": [
        "<specific behavioral/edge-case differences observed, if any>"
      ]
    },
    "semantic_similarity":         0.0,
    "semantic_similarity_rationale": "<2-5 sentences justifying the score>",
    "api_similarity":              0.0,
    "api_similarity_rationale":    "<2-5 sentences justifying the score>",
    "design_quality":              0.0,
    "design_quality_rationale":    "<2-5 sentences justifying the design score>",
    "implementation_quality_notes": "<free-form notes on quality issues>"
  }
}
```

## How to score `semantic_similarity` (0.0 to 1.0)

A holistic 0..1 score measuring whether the generated code preserves the *observable behavior* the original promises — independent of whether the API surface (names/signatures) matches. This is about **what the code does**, not what it is called. Consider:

1. **Behavioral equivalence** — Given the same inputs, does the generated code produce the same outputs as the original across the normal operating range?
2. **Edge cases & error handling** — Null/empty/boundary inputs, exception types raised, ordering guarantees, default values, numeric precision, overflow/underflow.
3. **Algorithmic fidelity** — Same effective algorithm/complexity and side effects (state mutation, I/O ordering), even if structured differently.
4. **Spec coverage** — Are all behaviors the original exposes actually implemented, or are non-trivial parts stubbed/simplified in a way that changes results?

Anchors:
- `1.0` — Behaviorally indistinguishable: identical outputs including edge cases, same errors, same ordering/defaults.
- `0.7-0.9` — Same core behavior; minor edge-case or error-type differences most callers would not hit.
- `0.4-0.6` — Core happy-path works but several behaviors diverge (edge cases, defaults, error handling) that change results in some scenarios.
- `0.1-0.3` — Only fragments of the intended behavior are reproduced.
- `0.0` — Empty, broken, or unrelated behavior.

## How to score `api_similarity` (0.0 to 1.0)

A holistic 0..1 score reflecting how closely the generated code matches the original at the **API surface** level — the names and shapes a client imports. Score this SEPARATELY from `semantic_similarity` (two trees can be behaviorally close yet API-divergent, or vice versa). Consider:

1. **Public surface alignment** — Public type names, method signatures (parameter types, return types), namespace/module paths.
2. **Idiomatic correctness** — Idiomatic for the target language (e.g. Ruby `nil` vs Float NaN, C# `Nullable<T>`, Kotlin sealed classes vs enums).
3. **Coverage of the public surface** — Did the generation expose all the public APIs the original does?

Anchors:
- `1.0` — Same public types, same methods with identical signatures and namespaces — a drop-in import.
- `0.7-0.9` — Names align, minor signature/namespace drift. Most clients would not notice.
- `0.4-0.6` — Recognizable but renamed APIs, missing methods, or restructured surface.
- `0.1-0.3` — Different surface and conventions; not import-compatible.
- `0.0` — Empty, broken, or unrelated.

## How to score `design_quality` (0.0 to 1.0)

A holistic 0..1 score judging how well the **generated** code honors sound architecture & engineering principles, scaled to the project's complexity. Judge the generated tree on its own merits, NOT how closely it mirrors the original. Consider:

1. **Scale-Driven Code Organization** — Physical structure matches domain complexity; no "god file"/mega-dispatcher, no over-engineering of a trivial problem.
2. **Separation of Concerns / Anti-Overfitting** — Core business logic decoupled from stdin/stdout and JSON parsing, with a thin adapter translating I/O into idiomatic core calls. Logic fused into the I/O dispatcher (overfit to the test harness) scores low.
3. **SOLID adherence (size-appropriate)** — Parsing, routing, validation, core execution, and output formatting are distinct units (SRP); engine extensible without modification (OCP); depends on abstractions (DIP).
4. **Robustness & Interface Design** — Idiomatic, elegant public surface hiding internal complexity; graceful edge-case handling with properly modeled errors rather than generic faults.

Anchors:
- `0.9-1.0` — Production-grade: structure matches scale, core/adapter cleanly separated, clear SRP units, idiomatic resilient interfaces.
- `0.6-0.8` — Mostly sound with some coupling or mixed responsibilities; refactorable without redesign.
- `0.3-0.5` — Layering intent visible but significant SoC violations (e.g. business logic inside the dispatcher), or structure not matching complexity.
- `0.1-0.2` — Monolithic "god file"/mega-switch overfit to the I/O contract, little separation, generic error handling.
- `0.0` — Empty or broken.

## Rules

- Do not run the code. This is a static review. Do not infer behavior from tests; only read source files in the in-scope paths.
- `semantic_similarity`, `api_similarity`, and `design_quality` are THREE INDEPENDENT scores. Do not let one anchor the others — a tree can be behaviorally faithful (high semantic) yet API-divergent (low api), or well-engineered (high design) yet behaviorally wrong (low semantic).
- Keep each rationale to 2–5 sentences. Be specific — cite concrete class/method/file names rather than generic statements.
- `implementation_quality_notes` captures things not reflected in the scores: code smells, unused parameters, suspicious patterns, or places where the generated code is *better* than the original.
- Write JSON exactly per the schema. Do not add or rename fields. Write ONLY the JSON file to `{OUTPUT_PATH}`.
