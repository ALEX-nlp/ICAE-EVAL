## Product Requirement Document

# Portable Neural-Network Inference Engine - Black-Box Evaluation Contract

## Project Goal

Build a lightweight inference engine that loads a trained neural network from a portable, self-contained text description (its "wire format") and evaluates it on demand. The goal is to let application developers run a previously trained network inside a production system without pulling in a heavyweight training framework or its native runtime. The engine supports three evaluation styles — a feed-forward pass, a recurrent sequence reduction, and a general multi-node computation graph — and emits the network's named outputs as plain text.

---

## Background & Problem

A neural network is normally trained in a large data-science framework. Shipping that whole framework into a latency-sensitive production service (an event filter, an online classifier, an embedded analytics pipeline) is impractical: it is heavy, hard to embed, and tied to a particular language runtime. Developers are otherwise forced to re-implement the trained network's arithmetic by hand for every deployment target, which is repetitive and error-prone, and tiny numerical discrepancies silently change predictions.

With this engine, a trained network is exported once into a self-contained description that fully captures the input variables (each with its normalization offset and scale), the layer/graph topology, the weights, and the named outputs. The engine reads that description and reproduces the network's predictions deterministically and reproducibly across runs, with no dependency on the original training framework.

The contract below specifies the engine purely in terms of observable behavior: a single self-describing command goes in, and a fixed, language-neutral text rendering of the network's outputs comes out. Nothing in this contract depends on the host language, the in-memory data model, or any particular file layout.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a non-trivial domain (configuration parsing, several layer/cell kinds, three evaluation strategies, numeric output formatting). It MUST NOT be a single "god file". Produce a clear, multi-file tree that separates configuration parsing, the core math/graph engine, the evaluation strategies, and the I/O adapter. Do not over-engineer, but avoid a monolith.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, NOT the internal data model. The core engine must be fully decoupled from stdin/stdout and from the command JSON. The adapter alone translates a command into idiomatic engine calls and renders results.

3. **Adherence to SOLID Design Principles** (scaled to project size):
   - **SRP:** Separate command parsing, configuration parsing, the evaluation strategy, the numeric core, and output formatting.
   - **OCP:** Adding a new layer/cell kind or a new evaluation strategy must not require modifying the core engine.
   - **LSP:** Every layer/cell kind must be substitutable wherever the engine expects a layer/cell.
   - **ISP:** Keep evaluation interfaces small and cohesive (a feed-forward network, a recurrent reducer, and a graph node should not share one fat interface).
   - **DIP:** The evaluation strategies depend on a layer abstraction, not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface (load a description → evaluate → read named outputs) must be elegant and idiomatic to the target language.
   - **Resilience:** Malformed commands, unknown modes, and invalid network descriptions must be handled gracefully and reported through a normalized, language-neutral error contract rather than crashing or leaking host-runtime fault details.

---

## Wire Format & I/O Contract

The execution adapter reads **exactly one** JSON command object from stdin and writes the rendered result to stdout. Every command carries a `mode` selector that chooses the evaluation strategy:

- `feed_forward` — evaluate a layered feed-forward network on a single input pattern.
- `recurrent` — fold an input sequence into a single output vector.
- `graph` — evaluate a general multi-node computation graph.

**Network description (`config`).** For `feed_forward` and `recurrent` the `config` object has the shape:
`{ "defaults": {var: value}, "inputs": [{"name", "offset", "scale"}], "layers": [...], "outputs": [name, ...] }`.
For `graph` the `config` object has the shape:
`{ "inputs": [{"name", "variables":[{"name","offset","scale"}]}], "input_sequences": [...], "nodes": [{"type","sources",...}], "layers": [...], "outputs": {name: {"labels":[...], "node_index"}} }`.

**Input preprocessing.** Every scalar input variable declares an `offset` and a `scale`. Before a value reaches the network it is transformed as `(value + offset) * scale`. Non-finite inputs (`nan`, `inf`, `-inf`, passed as string tokens) are replaced by the variable's declared default when one exists.

**Numeric output format.** Output values are rendered in the engine's default floating-point text form: roughly six significant figures, with trailing zeros and an unnecessary decimal point trimmed (e.g. `2`, `-3`, `0`, `0.880797`, `-4.06896e-05`). Integer-valued results print without a decimal point. This exact textual rendering is part of the contract.

**Output rendering by mode.**
- `feed_forward` and `recurrent` print one line per named output as `<name> <value>`, in the engine's output order.
- `graph` prints a header line `<output-node-name>:` followed by the node's value lines. With `op` = `compute` each value line is `<label> <value>`; with `op` = `scan` each line is `<label> <v1> <v2> ...` listing one value per sequence step.

**Error contract.** All failures are normalized to a single-line, language-neutral category on stdout, never a host-runtime stack trace:
- malformed command JSON → `error=invalid_command` then `detail=malformed_json`
- unrecognized `mode` → `error=unknown_mode` then `mode=<value>`
- an invalid/unsupported network description → `error=invalid_configuration`
- a runtime evaluation failure → `error=evaluation_failed`
- an output-rank mismatch → `error=output_rank_mismatch`

---

## Core Features

### Feature 1: Feed-Forward Dense Layer with Element-Wise Activations

**As a developer**, I want to evaluate a fully-connected (dense) layer and apply a named element-wise activation to its affine result, so I can reproduce the building block of any feed-forward classifier.

**Expected Behavior / Usage:**

In `feed_forward` mode the engine applies a dense layer (`output = activation(W·x + b)`), where `W` is given as a row-major flattened weight matrix. With identity weights and zero bias the affine result equals the (preprocessed) input, so the chosen activation is observable directly on the pre-activation values. The same pre-activation pair `(2, -3)` is transformed by `linear`, `sigmoid`, `rectified` (ReLU), and `tanh`. Each named output is printed on its own line as `<name> <value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_dense_activations.json`

```json
{
  "description": "Evaluate a single fully-connected layer (identity weights, zero bias) on a two-element input, applying a named element-wise activation to the affine result. Each case selects a different activation so the reader sees how the same pre-activation values (2, -3) are transformed.",
  "cases": [
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [
            { "name": "x0", "offset": 0.0, "scale": 1.0 },
            { "name": "x1", "offset": 0.0, "scale": 1.0 }
          ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0, 0.0, 0.0, 1.0 ],
              "bias": [ 0.0, 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": [ "a", "b" ]
        },
        "values": { "x0": 2.0, "x1": -3.0 }
      },
      "expected_output": "a 2\nb -3\n"
    },
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [
            { "name": "x0", "offset": 0.0, "scale": 1.0 },
            { "name": "x1", "offset": 0.0, "scale": 1.0 }
          ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0, 0.0, 0.0, 1.0 ],
              "bias": [ 0.0, 0.0 ],
              "activation": "sigmoid"
            }
          ],
          "outputs": [ "a", "b" ]
        },
        "values": { "x0": 2.0, "x1": -3.0 }
      },
      "expected_output": "a 0.880797\nb 0.0474259\n"
    },
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [
            { "name": "x0", "offset": 0.0, "scale": 1.0 },
            { "name": "x1", "offset": 0.0, "scale": 1.0 }
          ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0, 0.0, 0.0, 1.0 ],
              "bias": [ 0.0, 0.0 ],
              "activation": "rectified"
            }
          ],
          "outputs": [ "a", "b" ]
        },
        "values": { "x0": 2.0, "x1": -3.0 }
      },
      "expected_output": "a 2\nb 0\n"
    },
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [
            { "name": "x0", "offset": 0.0, "scale": 1.0 },
            { "name": "x1", "offset": 0.0, "scale": 1.0 }
          ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0, 0.0, 0.0, 1.0 ],
              "bias": [ 0.0, 0.0 ],
              "activation": "tanh"
            }
          ],
          "outputs": [ "a", "b" ]
        },
        "values": { "x0": 2.0, "x1": -3.0 }
      },
      "expected_output": "a 0.964028\nb -0.995055\n"
    }
  ]
}
```

---

### Feature 2: Input Preprocessing

**As a developer**, I want each input variable to be normalized and sanitized before it reaches the network, so the same exported network behaves identically regardless of the raw feature scale or occasional missing values.

**Expected Behavior / Usage:**

Every input variable carries an `offset` and a `scale`, and the engine maintains a table of per-variable `defaults`. Preprocessing happens before any layer math, so its effect can be observed through an identity dense layer.

*2.1 Affine normalization — each input is transformed as `(value + offset) * scale`.*

A single input flows through a linear identity layer, so the printed output is exactly the preprocessed value. The cases demonstrate both an offset+scale transform and a pure scaling.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_input_scaling.json`

```json
{
  "description": "Each named input is preprocessed as (value + offset) * scale before it reaches the network. A linear identity layer exposes the scaled value directly so the preprocessing transform is observable.",
  "cases": [
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [ { "name": "x0", "offset": -1.0, "scale": 2.0 } ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0 ],
              "bias": [ 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": [ "y" ]
        },
        "values": { "x0": 4.0 }
      },
      "expected_output": "y 6\n"
    },
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 0.5 } ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0 ],
              "bias": [ 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": [ "y" ]
        },
        "values": { "x0": 10.0 }
      },
      "expected_output": "y 5\n"
    }
  ]
}
```

*2.2 Default substitution for non-finite inputs — a non-finite value (`nan`, `inf`, `-inf`) is replaced by the variable's declared default before evaluation.*

Special inputs are supplied as the string tokens `nan` / `inf` / `-inf`. When a default is declared for the affected variable, the engine substitutes it, so the printed output reflects the default rather than a non-finite result.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_default_substitution.json`

```json
{
  "description": "When an input value is non-finite (NaN, +inf, -inf) and a default is declared for that variable, the engine substitutes the default before evaluation. Special inputs are passed as the string tokens nan/inf/-inf.",
  "cases": [
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": { "x0": 5.0 },
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0 ],
              "bias": [ 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": [ "y" ]
        },
        "values": { "x0": "nan" }
      },
      "expected_output": "y 5\n"
    },
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": { "x0": -2.0 },
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0 ],
              "bias": [ 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": [ "y" ]
        },
        "values": { "x0": "inf" }
      },
      "expected_output": "y -2\n"
    }
  ]
}
```

---

### Feature 3: Specialized Feed-Forward Layer Kinds

**As a developer**, I want the engine to support the specialized layer kinds that modern exported networks use beyond a plain dense layer, so I can deploy architectures that rely on per-feature normalization, maxout units, or highway gating.

**Expected Behavior / Usage:**

These layers plug into the same `feed_forward` pipeline as a dense layer (same input preprocessing, same `<name> <value>` rendering) but compute different functions.

*3.1 Per-feature normalization — `output_i = weight_i * (input_i + bias_i)` for each feature independently (an affine batch-normalization-style rescaling).*

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_normalization.json`

```json
{
  "description": "A per-feature normalization layer computes weight * (input + bias) for each element independently (an affine batch-normalization-style rescaling). Two independent features are normalized with distinct weight/bias pairs.",
  "cases": [
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [
            { "name": "x0", "offset": 0.0, "scale": 1.0 },
            { "name": "x1", "offset": 0.0, "scale": 1.0 }
          ],
          "layers": [
            {
              "architecture": "normalization",
              "weights": [ 2.0, 3.0 ],
              "bias": [ 1.0, -1.0 ],
              "activation": "linear"
            }
          ],
          "outputs": [ "a", "b" ]
        },
        "values": { "x0": 2.0, "x1": 2.0 }
      },
      "expected_output": "a 6\nb 3\n"
    },
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ],
          "layers": [
            {
              "architecture": "normalization",
              "weights": [ 0.5 ],
              "bias": [ 4.0 ],
              "activation": "linear"
            }
          ],
          "outputs": [ "y" ]
        },
        "values": { "x0": 6.0 }
      },
      "expected_output": "y 5\n"
    }
  ]
}
```

*3.2 Maxout layer — several parallel affine sub-layers; per output unit the layer emits the maximum over all sub-layers' pre-activations.*

A trailing linear identity layer exposes the selected maximum. The two cases pick different inputs so a different sub-layer "wins" each time.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_maxout.json`

```json
{
  "description": "A maxout layer holds several parallel affine sub-layers and, per output unit, emits the maximum over all sub-layers' pre-activations. A trailing linear identity layer exposes the selected maximum.",
  "cases": [
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ],
          "layers": [
            {
              "architecture": "maxout",
              "sublayers": [
                { "weights": [ 1.0 ], "bias": [ 0.0 ] },
                { "weights": [ -2.0 ], "bias": [ 1.0 ] }
              ]
            },
            {
              "architecture": "dense",
              "weights": [ 1.0 ],
              "bias": [ 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": [ "m" ]
        },
        "values": { "x0": 2.0 }
      },
      "expected_output": "m 2\n"
    },
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ],
          "layers": [
            {
              "architecture": "maxout",
              "sublayers": [
                { "weights": [ 1.0 ], "bias": [ 0.0 ] },
                { "weights": [ -2.0 ], "bias": [ 1.0 ] }
              ]
            },
            {
              "architecture": "dense",
              "weights": [ 1.0 ],
              "bias": [ 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": [ "m" ]
        },
        "values": { "x0": -1.0 }
      },
      "expected_output": "m 3\n"
    }
  ]
}
```

*3.3 Highway layer — blends a transformed branch and a carried-through branch via a learned gate: `output = H(x)·T(x) + x·(1 - T(x))`.*

A trailing linear identity layer exposes the gated result. The first case opens the transform gate fully (output follows the transformed branch); the second closes it (output carries the input through).

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_highway.json`

```json
{
  "description": "A highway layer mixes a transformed branch and a carried-through branch using learned transform/carry gates: output = H(x)*T(x) + x*(1 - T(x)). A trailing linear identity layer exposes the gated result.",
  "cases": [
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [
            { "name": "x0", "offset": 0.0, "scale": 1.0 },
            { "name": "x1", "offset": 0.0, "scale": 1.0 }
          ],
          "layers": [
            {
              "architecture": "highway",
              "activation": "rectified",
              "components": {
                "t": { "weights": [ 1.0, 0.0, 0.0, 1.0 ], "bias": [ 0.0, 0.0 ] },
                "carry": { "weights": [ 0.0, 0.0, 0.0, 0.0 ], "bias": [ 0.0, 0.0 ] }
              }
            },
            {
              "architecture": "dense",
              "weights": [ 1.0, 0.0, 0.0, 1.0 ],
              "bias": [ 0.0, 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": [ "a", "b" ]
        },
        "values": { "x0": 1.0, "x1": 1.0 }
      },
      "expected_output": "a 1\nb 1\n"
    },
    {
      "input": {
        "mode": "feed_forward",
        "config": {
          "defaults": {},
          "inputs": [
            { "name": "x0", "offset": 0.0, "scale": 1.0 },
            { "name": "x1", "offset": 0.0, "scale": 1.0 }
          ],
          "layers": [
            {
              "architecture": "highway",
              "activation": "rectified",
              "components": {
                "t": { "weights": [ 0.0, 0.0, 0.0, 0.0 ], "bias": [ -10.0, -10.0 ] },
                "carry": { "weights": [ 0.0, 0.0, 0.0, 0.0 ], "bias": [ 0.0, 0.0 ] }
              }
            },
            {
              "architecture": "dense",
              "weights": [ 1.0, 0.0, 0.0, 1.0 ],
              "bias": [ 0.0, 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": [ "a", "b" ]
        },
        "values": { "x0": 4.0, "x1": -5.0 }
      },
      "expected_output": "a 2\nb -2.5\n"
    }
  ]
}
```

---

### Feature 4: Recurrent Sequence Reduction

**As a developer**, I want to fold a multi-step input sequence into a single fixed-size state vector, so I can classify variable-length inputs from one exported network.

**Expected Behavior / Usage:**

In `recurrent` mode the command supplies a `sequence` object mapping each input channel to its ordered list of per-step values. The engine runs the recurrent layer across every step and prints the **final** state vector, one `<name> <value>` line per output element. Three cell kinds are covered, all reading the same wire shape (`components` with weight matrix `weights`, recurrent matrix `U`, and `bias`).

*4.1 Simple recurrent cell — `state_t = activation(W·x_t + U·state_{t-1} + b)`, with a zero initial state.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_simple_recurrent.json`

```json
{
  "description": "A simple recurrent layer folds an ordered sequence into a single fixed-size state vector. At each step the new state is activation(W*input + U*prev + b); the engine returns the final state. Input is one named channel sampled over several time steps.",
  "cases": [
    {
      "input": {
        "mode": "recurrent",
        "config": {
          "defaults": {},
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ],
          "layers": [
            {
              "architecture": "simplernn",
              "activation": "linear",
              "components": {
                "h": { "weights": [ 1.0 ], "U": [ 0.5 ], "bias": [ 0.0 ] }
              }
            }
          ],
          "outputs": [ "h0" ]
        },
        "sequence": { "x0": [ 1.0, 1.0, 1.0 ] }
      },
      "expected_output": "h0 1.75\n"
    },
    {
      "input": {
        "mode": "recurrent",
        "config": {
          "defaults": {},
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ],
          "layers": [
            {
              "architecture": "simplernn",
              "activation": "linear",
              "components": {
                "h": { "weights": [ 1.0 ], "U": [ 0.5 ], "bias": [ 0.0 ] }
              }
            }
          ],
          "outputs": [ "h0" ]
        },
        "sequence": { "x0": [ 2.0, -1.0 ] }
      },
      "expected_output": "h0 0\n"
    }
  ]
}
```

*4.2 Gated recurrent unit (GRU) — update and reset gates (inner activation) plus a candidate state (main activation) reduce the sequence to a final two-element state.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_gated_recurrent.json`

```json
{
  "description": "A gated recurrent layer reduces a sequence to a final state using update and reset gates (inner activation) plus a candidate state (main activation). Output is the final two-element state for the supplied single-channel sequence.",
  "cases": [
    {
      "input": {
        "mode": "recurrent",
        "config": {
          "defaults": {},
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ],
          "layers": [
            {
              "architecture": "gru",
              "activation": "tanh",
              "components": {
                "z": { "weights": [ 0.1, 0.2 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] },
                "r": { "weights": [ 0.1, 0.2 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] },
                "h": { "weights": [ 0.3, 0.4 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] }
              },
              "inner_activation": "sigmoid"
            }
          ],
          "outputs": [ "h0", "h1" ]
        },
        "sequence": { "x0": [ 1.0, 0.5, -0.5 ] }
      },
      "expected_output": "h0 -4.06896e-05\nh1 -0.00823268\n"
    },
    {
      "input": {
        "mode": "recurrent",
        "config": {
          "defaults": {},
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ],
          "layers": [
            {
              "architecture": "gru",
              "activation": "tanh",
              "components": {
                "z": { "weights": [ 0.1, 0.2 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] },
                "r": { "weights": [ 0.1, 0.2 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] },
                "h": { "weights": [ 0.3, 0.4 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] }
              },
              "inner_activation": "sigmoid"
            }
          ],
          "outputs": [ "h0", "h1" ]
        },
        "sequence": { "x0": [ 0.2, 0.2, 0.2, 0.2 ] }
      },
      "expected_output": "h0 0.0581038\nh1 0.0771669\n"
    }
  ]
}
```

*4.3 Long short-term memory (LSTM) — input, forget, and output gates over an internal cell state reduce the sequence to a final two-element hidden state.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_lstm_recurrent.json`

```json
{
  "description": "A long short-term memory layer reduces a sequence to a final hidden state using input, forget, and output gates over an internal cell state. Output is the final two-element hidden state for the supplied single-channel sequence.",
  "cases": [
    {
      "input": {
        "mode": "recurrent",
        "config": {
          "defaults": {},
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ],
          "layers": [
            {
              "architecture": "lstm",
              "activation": "tanh",
              "components": {
                "i": { "weights": [ 0.1, 0.2 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] },
                "f": { "weights": [ 0.1, 0.2 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] },
                "o": { "weights": [ 0.1, 0.2 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] },
                "c": { "weights": [ 0.3, 0.4 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] }
              },
              "inner_activation": "sigmoid"
            }
          ],
          "outputs": [ "h0", "h1" ]
        },
        "sequence": { "x0": [ 1.0, 0.5, -0.5 ] }
      },
      "expected_output": "h0 0.00439862\nh1 0.0077197\n"
    },
    {
      "input": {
        "mode": "recurrent",
        "config": {
          "defaults": {},
          "inputs": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ],
          "layers": [
            {
              "architecture": "lstm",
              "activation": "tanh",
              "components": {
                "i": { "weights": [ 0.1, 0.2 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] },
                "f": { "weights": [ 0.1, 0.2 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] },
                "o": { "weights": [ 0.1, 0.2 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] },
                "c": { "weights": [ 0.3, 0.4 ], "U": [ 0.1, 0.0, 0.0, 0.1 ], "bias": [ 0.0, 0.0 ] }
              },
              "inner_activation": "sigmoid"
            }
          ],
          "outputs": [ "h0", "h1" ]
        },
        "sequence": { "x0": [ -1.0, -1.0, 2.0 ] }
      },
      "expected_output": "h0 0.0960763\nh1 0.142141\n"
    }
  ]
}
```

---

### Feature 5: Computation-Graph Inference

**As a developer**, I want to evaluate a general multi-node network graph (multiple input nodes, optional sequence inputs, one or more output nodes), so I can deploy complex architectures — merges, concatenations, time-distributed layers, multiple heads — from a single exported description.

**Expected Behavior / Usage:**

In `graph` mode the `config` declares scalar input nodes (`inputs`), sequence input nodes (`input_sequences`), an ordered list of `nodes` (each with a `type` and `sources` indices), the shared `layers` pool, and a named `outputs` map. The command provides per-node values under `inputs` (scalar) and/or `sequences` (per-step), an `op` (`compute` or `scan`), and an optional `output` selecting which named output to evaluate. Every result is printed as a `<output-name>:` header followed by that node's value lines.

*5.1 Feed-forward through a graph — a single input node routed through a feed-forward node to one output.*

With `op` = `compute` the output prints a header then one `<label> <value>` line per output unit.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_graph_feedforward.json`

```json
{
  "description": "A computation graph routes a named input node through a feed-forward node to a named output node. The output block is printed as a header line '<output>:' followed by one '<label> <value>' line per output unit.",
  "cases": [
    {
      "input": {
        "mode": "graph",
        "config": {
          "inputs": [
            {
              "name": "node_0",
              "variables": [
                { "name": "x0", "offset": 0.0, "scale": 1.0 },
                { "name": "x1", "offset": 0.0, "scale": 1.0 }
              ]
            }
          ],
          "input_sequences": [],
          "nodes": [
            { "type": "input", "sources": [ 0 ], "size": 2 },
            { "type": "feed_forward", "sources": [ 0 ], "layer_index": 0 }
          ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0, 0.0, 0.0, 1.0 ],
              "bias": [ 0.0, 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": { "out": { "labels": [ "a", "b" ], "node_index": 1 } }
        },
        "op": "compute",
        "inputs": { "node_0": { "x0": 3.0, "x1": 4.0 } }
      },
      "expected_output": "out:\na 3\nb 4\n"
    },
    {
      "input": {
        "mode": "graph",
        "config": {
          "inputs": [
            {
              "name": "node_0",
              "variables": [
                { "name": "x0", "offset": 0.0, "scale": 1.0 },
                { "name": "x1", "offset": 0.0, "scale": 1.0 }
              ]
            }
          ],
          "input_sequences": [],
          "nodes": [
            { "type": "input", "sources": [ 0 ], "size": 2 },
            { "type": "feed_forward", "sources": [ 0 ], "layer_index": 0 }
          ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0, 0.0, 0.0, 1.0 ],
              "bias": [ 0.0, 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": { "out": { "labels": [ "a", "b" ], "node_index": 1 } }
        },
        "op": "compute",
        "inputs": { "node_0": { "x0": -2.0, "x1": 8.0 } }
      },
      "expected_output": "out:\na -2\nb 8\n"
    }
  ]
}
```

*5.2 Concatenate / multi-input fan-in — two independent input nodes merged by a concatenate node, then fed to a dense node.*

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_graph_concatenate.json`

```json
{
  "description": "A computation graph merges two independent input nodes with a concatenate node, then feeds the combined vector to a dense node that sums the two channels. Demonstrates multi-input fan-in within one graph.",
  "cases": [
    {
      "input": {
        "mode": "graph",
        "config": {
          "inputs": [
            { "name": "node_a", "variables": [ { "name": "u", "offset": 0.0, "scale": 1.0 } ] },
            { "name": "node_b", "variables": [ { "name": "v", "offset": 0.0, "scale": 1.0 } ] }
          ],
          "input_sequences": [],
          "nodes": [
            { "type": "input", "sources": [ 0 ], "size": 1 },
            { "type": "input", "sources": [ 1 ], "size": 1 },
            { "type": "concatenate", "sources": [ 0, 1 ] },
            { "type": "feed_forward", "sources": [ 2 ], "layer_index": 0 }
          ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0, 1.0 ],
              "bias": [ 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": { "merged": { "labels": [ "s" ], "node_index": 3 } }
        },
        "op": "compute",
        "inputs": { "node_a": { "u": 5.0 }, "node_b": { "v": 7.0 } }
      },
      "expected_output": "merged:\ns 12\n"
    },
    {
      "input": {
        "mode": "graph",
        "config": {
          "inputs": [
            { "name": "node_a", "variables": [ { "name": "u", "offset": 0.0, "scale": 1.0 } ] },
            { "name": "node_b", "variables": [ { "name": "v", "offset": 0.0, "scale": 1.0 } ] }
          ],
          "input_sequences": [],
          "nodes": [
            { "type": "input", "sources": [ 0 ], "size": 1 },
            { "type": "input", "sources": [ 1 ], "size": 1 },
            { "type": "concatenate", "sources": [ 0, 1 ] },
            { "type": "feed_forward", "sources": [ 2 ], "layer_index": 0 }
          ],
          "layers": [
            {
              "architecture": "dense",
              "weights": [ 1.0, 1.0 ],
              "bias": [ 0.0 ],
              "activation": "linear"
            }
          ],
          "outputs": { "merged": { "labels": [ "s" ], "node_index": 3 } }
        },
        "op": "compute",
        "inputs": { "node_a": { "u": -3.0 }, "node_b": { "v": 10.0 } }
      },
      "expected_output": "merged:\ns 7\n"
    }
  ]
}
```

*5.3 Multiple output heads with output selection — one graph exposing several named outputs; the caller names which output to evaluate.*

Only the selected output's header and values are emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_graph_multi_output.json`

```json
{
  "description": "A computation graph exposes several output nodes. The caller names which output to evaluate; only that output's header and values are emitted. Two cases select two different outputs from the same graph and input.",
  "cases": [
    {
      "input": {
        "mode": "graph",
        "config": {
          "inputs": [
            { "name": "node_0", "variables": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ] }
          ],
          "input_sequences": [],
          "nodes": [
            { "type": "input", "sources": [ 0 ], "size": 1 },
            { "type": "feed_forward", "sources": [ 0 ], "layer_index": 0 },
            { "type": "feed_forward", "sources": [ 0 ], "layer_index": 1 }
          ],
          "layers": [
            { "architecture": "dense", "weights": [ 2.0 ], "bias": [ 0.0 ], "activation": "linear" },
            { "architecture": "dense", "weights": [ 10.0 ], "bias": [ 1.0 ], "activation": "linear" }
          ],
          "outputs": {
            "double": { "labels": [ "d" ], "node_index": 1 },
            "scaled": { "labels": [ "s" ], "node_index": 2 }
          }
        },
        "op": "compute",
        "inputs": { "node_0": { "x0": 3.0 } },
        "output": "double"
      },
      "expected_output": "double:\nd 6\n"
    },
    {
      "input": {
        "mode": "graph",
        "config": {
          "inputs": [
            { "name": "node_0", "variables": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ] }
          ],
          "input_sequences": [],
          "nodes": [
            { "type": "input", "sources": [ 0 ], "size": 1 },
            { "type": "feed_forward", "sources": [ 0 ], "layer_index": 0 },
            { "type": "feed_forward", "sources": [ 0 ], "layer_index": 1 }
          ],
          "layers": [
            { "architecture": "dense", "weights": [ 2.0 ], "bias": [ 0.0 ], "activation": "linear" },
            { "architecture": "dense", "weights": [ 10.0 ], "bias": [ 1.0 ], "activation": "linear" }
          ],
          "outputs": {
            "double": { "labels": [ "d" ], "node_index": 1 },
            "scaled": { "labels": [ "s" ], "node_index": 2 }
          }
        },
        "op": "compute",
        "inputs": { "node_0": { "x0": 3.0 } },
        "output": "scaled"
      },
      "expected_output": "scaled:\ns 31\n"
    }
  ]
}
```

*5.4 Time-distributed sequence output (scan) — the same dense transform applied independently at every step of an input sequence, returning a full output sequence.*

With `op` = `scan` each label line lists one value per time step.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_graph_sequence_scan.json`

```json
{
  "description": "A computation graph applies the same dense transform independently at every time step of an input sequence (time-distributed), returning a full output sequence. The scan output prints each label followed by one value per time step.",
  "cases": [
    {
      "input": {
        "mode": "graph",
        "config": {
          "inputs": [],
          "input_sequences": [
            { "name": "seq_0", "variables": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ] }
          ],
          "nodes": [
            { "type": "input_sequence", "sources": [ 0 ], "size": 1 },
            { "type": "time_distributed", "sources": [ 0 ], "layer_index": 0 }
          ],
          "layers": [
            { "architecture": "dense", "weights": [ 2.0 ], "bias": [ 1.0 ], "activation": "linear" }
          ],
          "outputs": { "out": { "labels": [ "y" ], "node_index": 1 } }
        },
        "op": "scan",
        "sequences": { "seq_0": { "x0": [ 1.0, 2.0, 3.0 ] } }
      },
      "expected_output": "out:\ny 3 5 7\n"
    },
    {
      "input": {
        "mode": "graph",
        "config": {
          "inputs": [],
          "input_sequences": [
            { "name": "seq_0", "variables": [ { "name": "x0", "offset": 0.0, "scale": 1.0 } ] }
          ],
          "nodes": [
            { "type": "input_sequence", "sources": [ 0 ], "size": 1 },
            { "type": "time_distributed", "sources": [ 0 ], "layer_index": 0 }
          ],
          "layers": [
            { "architecture": "dense", "weights": [ 2.0 ], "bias": [ 1.0 ], "activation": "linear" }
          ],
          "outputs": { "out": { "labels": [ "y" ], "node_index": 1 } }
        },
        "op": "scan",
        "sequences": { "seq_0": { "x0": [ 0.0, -1.0 ] } }
      },
      "expected_output": "out:\ny 1 -1\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the inference engine: a configuration parser that reads the network wire format, a numeric core with substitutable layer/cell kinds (dense, normalization, maxout, highway; simple-recurrent, GRU, LSTM cells; graph node types), the three evaluation strategies (feed-forward, recurrent reduction, multi-node graph), input preprocessing with default substitution, and an output formatter. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core engine. It reads one JSON command from stdin in the wire format described above (a `mode` selector plus a `config` and the input data), invokes the matching evaluation strategy, and prints the engine's result to stdout exactly matching the per-feature contracts above. The adapter is logically (and ideally physically) separated from the core domain. All errors are normalized to the single-line, language-neutral category contract on stdout (`error=invalid_command`, `error=unknown_mode`, `error=invalid_configuration`, `error=evaluation_failed`, `error=output_rank_mismatch`); the adapter never leaks host-runtime exception identities.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_dense_activations.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_dense_activations@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
