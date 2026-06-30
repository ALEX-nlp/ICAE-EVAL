## Product Requirement Document

We need a standalone statistics computation service that developers can call from the command line. The tool should accept a single instruction over standard input and return the result to standard output. At a high level, it needs to support three categories of functionality: summarizing collections of numbers (like finding the center and spread of a dataset), evaluating various probability models for both discrete and continuous scenarios, and running standard hypothesis tests to help decide whether data supports a given assumption.

For probability models, we need to cover the common shapes — things like coin-flip style models, count-based models, bell-curve models, and several others. Each model should expose the typical properties developers ask about (densities, cumulative probabilities, means, modes, etc.).

For the hypothesis tests, we want at least four or five standard tests — the kind you'd find in an intro statistics textbook. Results should be reported as structured key-value output so they're easy to parse.

The tool should handle edge cases gracefully: invalid inputs should return a designated sentinel value rather than crashing, and errors should be surfaced as a readable error message rather than a stack trace. For output formatting, handle it the same way the existing rank-correlation feature does when reporting per-item detail. The optional rounding parameter behavior should match what the chi-squared test module does for its composite output.

All numeric results should use the platform's default floating-point representation, and non-finite values should be rendered as human-readable words rather than raw symbols.