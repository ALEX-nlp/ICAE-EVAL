## Product Requirement Document

# Tax-Benefit Microsimulation Engine — Periods, Scales, Parameters & Household Calculations - Behavioral Contract

## Project Goal

Build a reusable microsimulation engine for tax and benefit rules that allows developers to model dated inputs, progressive bracket scales, time-varying legislative parameters, and household structures, then ask for calculated results with consistent vectorized semantics — without hand-writing repetitive period arithmetic, bracket math, parameter-validity bookkeeping, and entity membership logic for every rule.

---

## Background & Problem

Without this engine, developers are forced to manually parse and format period expressions, expand a year into months, implement progressive amount/rate brackets and their inverse and average-rate views, look up legislative values that change at known dates, validate multi-person household payloads, and aggregate per-month results into yearly totals or prorate yearly values to a month. This leads to repetitive, error-prone boilerplate, inconsistent boundary handling at validity edges, and fragile simulations whenever a calculation spans several months, several people, or several parameter validity ranges.

With this engine, developers declare situations, periods, parameters, and bracket scales as plain data, then request a calculated quantity. The engine returns vector results with predictable rounding, surfaces out-of-range lookups as explicit not-found conditions, and reports malformed inputs as neutral, language-independent error categories.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain is broad (temporal algebra, bracket math, parameter resolution, entity modelling, a calculation engine) and warrants a multi-module layout.

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
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults. In the stdout contract every error MUST be rendered as a neutral category line such as `error="invalid_input"` — never leak a host-language exception class name or runtime message.

---

## Core Features

### Feature 1: Period Expressions

**As a developer**, I want to parse, format, and subdivide calendar period expressions, so I can accept compact period strings, render them back canonically, and iterate over the smaller periods they cover without writing date arithmetic by hand.

**Expected Behavior / Usage:**

A period is a triple of a unit (`"year"` or `"month"`), a first instant (a `YYYY-MM-DD` calendar day), and a positive length counting how many units it spans. The canonical short string form collapses common cases: a 1-unit year starting in January is just the year (`"2014"`); twelve months starting in January is also that year; a single month is `"YYYY-MM"`; anything that does not collapse is written `"<unit>:<start>:<length>"`, dropping the trailing `:1` (e.g. a year that does not start in January is `"year:2014-03"`).

*1.1 Parse a period expression — String to period*

The adapter receives one period expression as input. For a valid expression it prints the canonical period string, the unit, the first instant, and the length. Malformed expressions (a year with a count but no `year:` prefix like `2014:2`, a malformed month, a day-level granularity, an ambiguous `month:2014`, an empty string, a null, or a non-string container) print a neutral error category and echo the rejected selector.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_period_parse.json`

```json
{
    "description": "Parse a compact period expression into its unit, first instant and length, reporting a neutral error category and echoing the rejected selector for malformed expressions.",
    "cases": [
        {
            "input": "2014",
            "expected_output": "period=\"2014\"\nunit=\"year\"\nstart=\"2014-01-01\"\nlength=1\n"
        },
        {
            "input": "2014-01",
            "expected_output": "period=\"2014-01\"\nunit=\"month\"\nstart=\"2014-01-01\"\nlength=1\n"
        },
        {
            "input": "year:2014-03",
            "expected_output": "period=\"year:2014-03\"\nunit=\"year\"\nstart=\"2014-03-01\"\nlength=1\n"
        },
        {
            "input": "month:2014-03:3",
            "expected_output": "period=\"month:2014-03:3\"\nunit=\"month\"\nstart=\"2014-03-01\"\nlength=3\n"
        }
    ]
}
```

*1.2 Format a period — Period to string*

The adapter receives a period as its unit, first instant, and length, and prints only the canonical short string form, applying the collapsing rules above.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_period_format.json`

```json
{
    "description": "Render a period given by its unit, first instant and length back to its canonical short string form.",
    "cases": [
        {
            "input": {
                "unit": "year",
                "start": "2014-01-01",
                "size": 1
            },
            "expected_output": "period=\"2014\"\n"
        },
        {
            "input": {
                "unit": "month",
                "start": "2014-01-01",
                "size": 12
            },
            "expected_output": "period=\"2014\"\n"
        },
        {
            "input": {
                "unit": "month",
                "start": "2014-03-01",
                "size": 12
            },
            "expected_output": "period=\"year:2014-03\"\n"
        }
    ]
}
```

*1.3 Subdivide a period*

The adapter receives a period expression and a requested smaller unit, and prints the count of produced subperiods plus the first, the last, and the full ordered, inclusive list of subperiod labels in chronological order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_period_subdivision.json`

```json
{
    "description": "Expand a period into the ordered, inclusive list of smaller periods of a requested unit.",
    "cases": [
        {
            "input": {
                "period": "2017",
                "unit": "month"
            },
            "expected_output": "count=12\nfirst=\"2017-01\"\nlast=\"2017-12\"\nitems=[\"2017-01\",\"2017-02\",\"2017-03\",\"2017-04\",\"2017-05\",\"2017-06\",\"2017-07\",\"2017-08\",\"2017-09\",\"2017-10\",\"2017-11\",\"2017-12\"]\n"
        },
        {
            "input": {
                "period": "year:2014:2",
                "unit": "month"
            },
            "expected_output": "count=24\nfirst=\"2014-01\"\nlast=\"2015-12\"\nitems=[\"2014-01\",\"2014-02\",\"2014-03\",\"2014-04\",\"2014-05\",\"2014-06\",\"2014-07\",\"2014-08\",\"2014-09\",\"2014-10\",\"2014-11\",\"2014-12\",\"2015-01\",\"2015-02\",\"2015-03\",\"2015-04\",\"2015-05\",\"2015-06\",\"2015-07\",\"2015-08\",\"2015-09\",\"2015-10\",\"2015-11\",\"2015-12\"]\n"
        }
    ]
}
```

---

### Feature 2: Progressive Tax & Contribution Scales

**As a developer**, I want to express bracket-based scales and apply them to vectors, so I can compute liabilities, convert between marginal and average views, recover gross from net, and stack several scales together.

**Expected Behavior / Usage:**

A scale is an ordered list of brackets. The engine applies a scale to a numeric base vector element-wise and returns a numeric result vector. Numbers are rendered compactly: integers without a decimal point, non-integers rounded to at most ten decimals, positive/negative infinity as the markers `"Infinity"`/`"-Infinity"`.

*2.1 Fixed-amount scale*

Each bracket is a threshold and a fixed amount. For each base value the result is the sum of the amounts of every bracket whose threshold the value reaches; a value below the first threshold yields zero.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_amount_scale.json`

```json
{
    "description": "Apply a fixed-amount bracket scale: each base value accumulates the amounts of every bracket whose threshold it reaches; values below the first threshold yield zero.",
    "cases": [
        {
            "input": {
                "brackets": [
                    {
                        "threshold": 6,
                        "amount": 0.23
                    },
                    {
                        "threshold": 9,
                        "amount": 0.29
                    }
                ],
                "base": [
                    1,
                    8,
                    10
                ]
            },
            "expected_output": "liability=[0,0.23,0.52]\n"
        }
    ]
}
```

*2.2 Marginal-rate charge*

Each bracket is a threshold and a marginal rate that applies to the portion of the base between that threshold and the next. The result is the total marginal charge per base value. An optional rounding instruction rounds the base to a given number of decimals before the brackets are applied (banker-style half-to-even rounding on the base), which can change the charge near a rounding edge.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_marginal_charge.json`

```json
{
    "description": "Apply a marginal-rate bracket scale to a base vector, with optional rounding of the base to a given number of decimals before the brackets are applied.",
    "cases": [
        {
            "input": {
                "brackets": [
                    {
                        "threshold": 0,
                        "rate": 0
                    },
                    {
                        "threshold": 1,
                        "rate": 0.1
                    },
                    {
                        "threshold": 2,
                        "rate": 0.2
                    },
                    {
                        "threshold": 3,
                        "rate": 0
                    }
                ],
                "base": [
                    1,
                    1.5,
                    2,
                    2.5,
                    3.0,
                    4.0
                ]
            },
            "expected_output": "liability=[0,0.05,0.1,0.2,0.3,0.3]\n"
        },
        {
            "input": {
                "brackets": [
                    {
                        "threshold": 0,
                        "rate": 0
                    },
                    {
                        "threshold": 1,
                        "rate": 0.1
                    },
                    {
                        "threshold": 2,
                        "rate": 0.2
                    }
                ],
                "base": [
                    1,
                    1.5,
                    2,
                    2.5
                ]
            },
            "expected_output": "liability=[0,0.05,0.1,0.2]\n"
        }
    ]
}
```

*2.3 Average-rate view*

A marginal-rate scale can be re-expressed as an average-rate scale. The adapter prints the average thresholds (the last is unbounded, rendered as `"Infinity"`), the average rates at those thresholds, and the average-rate liability for a base vector.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_average_view.json`

```json
{
    "description": "Convert a marginal-rate scale into its equivalent average-rate view, exposing the average thresholds, average rates, and the average-rate liability for a base vector.",
    "cases": [
        {
            "input": {
                "brackets": [
                    {
                        "threshold": 0,
                        "rate": 0
                    },
                    {
                        "threshold": 1,
                        "rate": 0.1
                    },
                    {
                        "threshold": 2,
                        "rate": 0.2
                    }
                ],
                "base": [
                    1,
                    1.5,
                    2,
                    2.5
                ]
            },
            "expected_output": "average_thresholds=[0,1,2,\"Infinity\"]\naverage_rates=[0,0,0.05,0.2]\naverage_liability=[0,0.0375,0.1,0.125]\n"
        }
    ]
}
```

*2.4 Inverse net-to-gross recovery*

Given a marginal-rate scale, the engine derives net values from gross values (`net = gross - charge(gross)`) and exposes an inverse scale whose application to the net values recovers the original gross. The adapter prints the net vector and the recovered gross vector.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_inverse_recovery.json`

```json
{
    "description": "Given a marginal-rate scale, derive net values from gross values and verify the inverse scale recovers the original gross from the net.",
    "cases": [
        {
            "input": {
                "brackets": [
                    {
                        "threshold": 0,
                        "rate": 0
                    },
                    {
                        "threshold": 1,
                        "rate": 0.1
                    },
                    {
                        "threshold": 3,
                        "rate": 0.05
                    }
                ],
                "gross": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6
                ]
            },
            "expected_output": "net=[1,1.9,2.8,3.75,4.7,5.65]\nrecovered_gross=[1,2,3,4,5,6]\n"
        }
    ]
}
```

*2.5 Combining stacked scales*

Several marginal-rate scales, each given as dated brackets and evaluated at one instant, can be merged into a single scale. The merged scale uses the union of all thresholds; at each threshold the merged rate is the sum of the contributing scales' rates.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_combine_scales.json`

```json
{
    "description": "Stack several marginal-rate scales (each given as dated brackets) evaluated at an instant into a single merged scale, reporting the union of thresholds and the summed rates.",
    "cases": [
        {
            "input": {
                "instant": "2015",
                "scales": {
                    "health": {
                        "brackets": [
                            {
                                "rate": {
                                    "2015-01-01": 0.05
                                },
                                "threshold": {
                                    "2015-01-01": 0
                                }
                            },
                            {
                                "rate": {
                                    "2015-01-01": 0.1
                                },
                                "threshold": {
                                    "2015-01-01": 2000
                                }
                            }
                        ]
                    },
                    "retirement": {
                        "brackets": [
                            {
                                "rate": {
                                    "2015-01-01": 0.02
                                },
                                "threshold": {
                                    "2015-01-01": 0
                                }
                            },
                            {
                                "rate": {
                                    "2015-01-01": 0.04
                                },
                                "threshold": {
                                    "2015-01-01": 3000
                                }
                            }
                        ]
                    }
                }
            },
            "expected_output": "combined_thresholds=[0,2000,3000]\n[a specific composite rate set]\n"
        }
    ]
}
```

---

### Feature 3: Average Rate Analysis

**As a developer**, I want to derive the average rate between a target quantity and a varying denominator, so I can compare net and gross quantities across a vector, including the zero-denominator boundary.

**Expected Behavior / Usage:**

The adapter receives a target numeric vector and a single varying denominator. It prints the element-wise average rate computed as `1 - target / varying`. When the denominator is zero, the corresponding element is rendered as a neutral infinity marker rather than raising a host-language error.

**Test Cases:** `rcb_tests/public_test_cases/feature3_average_rate.json`

```json
{
    "description": "Compute the element-wise average rate of a target vector against a varying denominator, emitting a neutral infinity marker when the denominator is zero.",
    "cases": [
        {
            "input": {
                "target": [
                    1,
                    2,
                    3
                ],
                "varying": 2
            },
            "expected_output": "average_rate=[0.5,0,-0.5]\n"
        },
        {
            "input": {
                "target": [
                    1,
                    2,
                    3
                ],
                "varying": 0
            },
            "expected_output": "average_rate=[\"-Infinity\",\"-Infinity\",\"-Infinity\"]\n"
        }
    ]
}
```

---

### Feature 4: Threshold-Based Vector Selection

**As a developer**, I want to map each value of a vector to a configured choice according to ordered thresholds, so I can express piecewise rules without manual branching.

**Expected Behavior / Usage:**

The adapter receives a values vector, a thresholds list, and a choices list. For each value it selects the choice for the first band the value falls into (a value is "in" a band when it is less than or equal to that band's threshold). The choices list may contain exactly one more entry than the thresholds list (a final choice for values above the highest threshold) or exactly as many entries (values above the highest threshold then select zero). A threshold may be a per-position vector instead of a scalar. Any other threshold/choice cardinality is reported as a neutral configuration error. Boolean choices are rendered as `true`/`false`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_threshold_choices.json`

```json
{
    "description": "Select, for each input value, the choice matching the first threshold band it falls into; thresholds may be scalar or per-position vectors, and an invalid threshold/choice cardinality is a neutral error.",
    "cases": [
        {
            "input": {
                "values": [
                    4,
                    5,
                    6,
                    7,
                    8
                ],
                "thresholds": [
                    5,
                    7
                ],
                "choices": [
                    10,
                    15,
                    20
                ]
            },
            "expected_output": "selection=[10,10,15,15,20]\n"
        },
        {
            "input": {
                "values": [
                    4,
                    6,
                    8
                ],
                "thresholds": [
                    5,
                    7
                ],
                "choices": [
                    10,
                    20
                ]
            },
            "expected_output": "selection=[10,20,0]\n"
        },
        {
            "input": {
                "values": [
                    1000,
                    1000,
                    1000
                ],
                "thresholds": [
                    [
                        500,
                        1500,
                        1000
                    ]
                ],
                "choices": [
                    true,
                    false
                ]
            },
            "expected_output": "selection=[0,1,1]\n"
        }
    ]
}
```

---

### Feature 5: Dated Parameter Resolution

**As a developer**, I want to resolve a legislative value that changes at known dates, so I can read the value in force at any instant and detect when a value does not yet exist or has been stopped.

**Expected Behavior / Usage:**

The adapter receives a parameter tree whose leaves carry dated values (a map of `YYYY-MM-DD` start dates to values), a dotted path into the tree, and a query instant. It prints the path, the instant, and the value that is in force at that instant (the value of the most recent start date not after the instant). A request before the earliest start date, or at/after a date whose value has been explicitly stopped (set to null), is reported as a neutral parameter-not-found error that echoes the path and instant.

**Test Cases:** `rcb_tests/public_test_cases/feature5_parameter_lookup.json`

```json
{
    "description": "Resolve a dated scalar parameter from a parameter tree at a requested instant, returning the value in force; a request before a parameter exists or after it is stopped is a neutral not-found error.",
    "cases": [
        {
            "input": {
                "parameters": {
                    "income_tax_rate": {
                        "values": {
                            "2015-01-01": 0.15,
                            "2014-01-01": 0.14,
                            "2013-01-01": 0.13,
                            "2012-01-01": 0.16
                        }
                    }
                },
                "path": "income_tax_rate",
                "instant": "2015-06-01"
            },
            "expected_output": "path=\"income_tax_rate\"\ninstant=\"2015-06-01\"\nvalue=0.15\n"
        },
        {
            "input": {
                "parameters": {
                    "income_tax_rate": {
                        "values": {
                            "2015-01-01": 0.15,
                            "2014-01-01": 0.14,
                            "2013-01-01": 0.13,
                            "2012-01-01": 0.16
                        }
                    }
                },
                "path": "income_tax_rate",
                "instant": "2014-06-01"
            },
            "expected_output": "path=\"income_tax_rate\"\ninstant=\"2014-06-01\"\nvalue=0.14\n"
        }
    ]
}
```

---

### Feature 6: Household Situation Modelling

**As a developer**, I want to describe a household as people grouped by role and have the engine derive the membership structure and read stored group values, so I can drive multi-person calculations from a relational situation rather than hand-indexed arrays.

**Expected Behavior / Usage:**

A situation lists individual persons and the households grouping them. Within a household, members hold one of two roles: a parent role that admits at most two members (the first is labelled `first_parent`, the second `second_parent`) and a child role with no limit (labelled `child`). The order of persons follows the order in which they appear across households.

*6.1 Membership structure*

Given a situation, the adapter prints the ordered person identifiers, the ordered household identifiers, and four per-person vectors: the index of the owning household, the role key, the legacy role number (the two parents get 0 and 1, then children continue 2, 3, …, restarting per household), and the 0-based position within the household.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_household_membership.json`

```json
{
    "description": "From a situation of persons and households (each grouping members as parents and children), derive the ordered person and household identifiers and, per person, the owning household index, role key, legacy role number and position within the household.",
    "cases": [
        {
            "input": {
                "persons": {
                    "bill": {},
                    "bob": {},
                    "claudia": {},
                    "janet": {},
                    "tom": {}
                },
                "households": {
                    "first_household": {
                        "parents": [
                            "bill",
                            "bob"
                        ],
                        "children": [
                            "janet",
                            "tom"
                        ]
                    },
                    "second_household": {
                        "parents": [
                            "claudia"
                        ]
                    }
                }
            },
            "expected_output": "persons=[\"bill\",\"bob\",\"claudia\",\"janet\",\"tom\"]\nhouseholds=[\"first_household\",\"second_household\"]\nhousehold_by_person=[0,0,1,0,0]\nrole_by_person=[\"first_parent\",\"second_parent\",\"first_parent\",\"child\",\"child\"]\nlegacy_role_by_person=[0,1,0,2,3]\nposition_by_person=[0,1,0,2,3]\n"
        }
    ]
}
```

*6.2 Situation validation & normalization*

Given a list-form situation (persons and households as arrays), the adapter validates and normalizes it: it auto-assigns missing household identifiers, adds the required group entity when omitted, coerces a single member reference into a one-element list, and fills missing role lists with empty arrays. It prints the sorted entity collection names plus the normalized households and persons. A reference to an unknown entity collection, a variable placed on the wrong entity, or an unknown variable is reported as a neutral error.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_situation_validation.json`

```json
{
    "description": "Validate and normalise a list-form situation: auto-assign missing identifiers and required group entities, coerce a single member id into a list, and report a neutral error for malformed situations.",
    "cases": [
        {
            "input": {
                "persons": [
                    {
                        "id": 0,
                        "salary": 1
                    }
                ],
                "households": [
                    {
                        "parents": [
                            "0"
                        ]
                    }
                ]
            },
            "expected_output": "entities=[\"households\",\"persons\"]\nhouseholds=[{\"children\":[],\"id\":0,\"parents\":[\"0\"]}]\npersons=[{\"id\":0,\"salary\":1.0}]\n"
        },
        {
            "input": {
                "persons": [
                    {
                        "id": 0,
                        "salary": 1
                    }
                ],
                "households": [
                    {
                        "parents": 0
                    }
                ]
            },
            "expected_output": "entities=[\"households\",\"persons\"]\nhouseholds=[{\"children\":[],\"id\":0,\"parents\":[0]}]\npersons=[{\"id\":0,\"salary\":1.0}]\n"
        }
    ]
}
```

*6.3 Reading stored group values*

Given a structured situation with dated values stored on a group entity, an entity selector, a variable name, and a period, the adapter prints the entity, variable, period, and the vector of stored values in household order.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_entity_values.json`

```json
{
    "description": "Read a stored group-entity variable from a structured situation at a requested period, returning the values in household order.",
    "cases": [
        {
            "input": {
                "situation": {
                    "persons": {
                        "bill": {},
                        "bob": {},
                        "claudia": {},
                        "janet": {},
                        "tom": {}
                    },
                    "households": {
                        "first_household": {
                            "parents": [
                                "bill",
                                "bob"
                            ],
                            "children": [
                                "janet",
                                "tom"
                            ],
                            "rent": {
                                "2017-06": 800
                            }
                        },
                        "second_household": {
                            "parents": [
                                "claudia"
                            ],
                            "rent": {
                                "2017-06": 600
                            }
                        }
                    }
                },
                "entity": "household",
                "variable": "rent",
                "period": "2017-06"
            },
            "expected_output": "entity=\"household\"\nvariable=\"rent\"\nperiod=\"2017-06\"\nvalues=[800,600]\n"
        }
    ]
}
```

---

### Feature 7: Variable Calculation Engine

**As a developer**, I want to declare a household's monthly inputs and ask the engine to calculate derived variables over arbitrary periods, so I can evaluate monetary and status quantities with direct, summed, prorated, and grid-expanded semantics.

**Expected Behavior / Usage:**

The engine is exercised against a worked-example tax-benefit domain with these stated rules: a person's monthly **income tax** equals 15% of that month's salary; a person's monthly **social contribution** is a progressive marginal scale on salary (rates 2% up to 6 000, then 6% up to 12 600, then 12% above, per month); a household's annual **housing tax** for an accommodation of 100 m² occupied by a tenant is 1 000 currency units. Each result line prints the requested variable, the query period, and the calculated vector.

*7.1 Single-household variable calculation*

Given an input period, declared input variables, a requested variable, a query period, and an optional aggregation mode, the adapter calculates the variable: the default reads the value directly at the query period; the year-total mode sums the twelve monthly values of a year; the month-share mode prorates a yearly value to one month (one twelfth). An unknown variable is reported as a neutral not-found error.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_variable_calculation.json`

```json
{
    "description": "Calculate a dated variable for a single household from declared monthly inputs: a direct read, a year-total aggregation that sums months, a month-share aggregation that prorates a yearly value, a progressive-scale derived variable, and a neutral not-found error for an unknown variable.",
    "cases": [
        {
            "input": {
                "period": "2016-01",
                "input_variables": {
                    "salary": 2000
                },
                "variable": "salary",
                "query_period": "2016-01"
            },
            "expected_output": "variable=\"salary\"\nperiod=\"2016-01\"\nvalues=[2000]\n"
        },
        {
            "input": {
                "period": "2016-01",
                "input_variables": {
                    "salary": 2000
                },
                "variable": "income_tax",
                "query_period": "2016-01"
            },
            "expected_output": "variable=\"income_tax\"\nperiod=\"2016-01\"\nvalues=[300]\n"
        },
        {
            "input": {
                "period": "2016",
                "input_variables": {
                    "salary": 24000
                },
                "variable": "income_tax",
                "query_period": "2016",
                "aggregation": "year_total"
            },
            "expected_output": "variable=\"income_tax\"\nperiod=\"2016\"\nvalues=[3600]\n"
        }
    ]
}
```

*7.2 Axis-based grid expansion*

Given one or more axes — each naming a member input, a step count, and a minimum/maximum — the adapter expands the base household into a grid of variants. A single axis interpolates the named input linearly between minimum and maximum over the step count; parallel axes advance together and assign generated values to the configured member index. It prints the variable, query period, and the generated result vector.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_axis_expansion.json`

```json
{
    "description": "Expand a base household along one or more axes that interpolate a member input between a minimum and maximum over a fixed count of steps, then evaluate a variable over the generated grid.",
    "cases": [
        {
            "input": {
                "axes": [
                    {
                        "count": 3,
                        "name": "salary",
                        "min": 0,
                        "max": 3000
                    }
                ],
                "period": "2016-01",
                "parent1": {},
                "variable": "salary",
                "query_period": "2016-01"
            },
            "expected_output": "variable=\"salary\"\nperiod=\"2016-01\"\nvalues=[0,1500,3000]\n"
        }
    ]
}
```

*7.3 Enumerated input round-trip*

A household status variable takes one of an ordered set of categories (`owner`, `tenant`, `free_lodger`, `homeless`, indexed 0–3). The adapter accepts the status supplied as a category label through the input mechanism and reads it back as its stable numeric code.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_enum_input.json`

```json
{
    "description": "Accept an enumerated household status supplied either as a label or as a numeric code through the input mechanism, and read it back as a stable numeric code.",
    "cases": [
        {
            "input": {
                "household": "couple",
                "variable": "housing_occupancy_status",
                "period": "2017-12",
                "value": [
                    "free_lodger"
                ]
            },
            "expected_output": "variable=\"housing_occupancy_status\"\ncodes=[2]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_period_parse.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_period_parse@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the convention for infinite scaling limits
- reference the specific neutral error protocol
