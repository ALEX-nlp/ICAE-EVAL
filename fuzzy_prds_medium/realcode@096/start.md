## Product Requirement Document

Hey team, we need to build out this text classification and semantic search toolkit that's been on the backlog. The core idea is developers drop in plain text and get back useful signals — categories, scores, ranked docs, that kind of thing. We had a similar pipeline in the old recommendation engine (you can probably grep around for how we handled the scoring edge cases there), so let's not reinvent the wheel too much.

Main things I care about: the tokenizer needs to be smart about what it keeps vs throws away depending on config, the Bayes classifier should handle the case where someone queries something totally foreign to the training data (users have been complaining the old one just confidently returns garbage instead of saying 'I don't know'), and the semantic index piece needs to stay usable even after someone reorganizes which documents belong to which bucket — without having to blow everything away and start over.

Also there's been a recurring complaint that when people index a document that's basically just filler words, the system silently accepts it and then behaves weirdly downstream. We want a clear signal when that happens.

One more thing — the serialization story needs to actually work end to end. Someone on the data team tried to save and reload an index last sprint and the rankings came back different. That's a blocker.

Let's make sure the output format is consistent and deterministic across all these features. cc @backend-platform

A couple follow-ups from the questions that came in. On the token counting side, the behavior around punctuation needs to stay very explicit. When include_punctuation is true, individual punctuation characters like '!', '.', and "'" are their own tokens and get counted independently. They still go through the same stopword removal logic as the word tokens. When include_punctuation=false, punctuation tokens are excluded entirely before counting. That’s the same general expectation for the tokenization normalization piece in Feature 1 too: when include_punctuation=true, punctuation characters are kept as tokens but stopwords are still removed; when false, both punctuation and stopwords are excluded. Also, the output here should be token=count pairs sorted lexically.

For the vector reporting bit, each vector should come back as two lines in the same format every time: 'vector_N_length=<len>' and then either 'vector_N_zero=yes' or 'vector_N_zero=no'. Vectors are indexed from 0. An empty vector with length 0 counts as a zero vector, so that should output 'vector_N_zero=yes', and a vector containing only 0 values should also output 'yes'.

On the decomposition output, please keep it dead simple and line-based. We want input_rows, input_columns, left_rows, left_columns, right_rows, right_columns, and singular_values, all using the '=' delimiter format, one per line. singular_values should be comma-separated values rounded to two decimal places.

For training behavior, if auto_categorize is false and someone tries to train with a category label we don’t know, the system should return exactly 'error=category_not_found\ncategory=<label>\n' and not modify state at all. If auto_categorize is true, then we create the category automatically and report the updated sorted category list and count.

Also confirming the low-confidence classification behavior since a few people asked the same thing in different ways: if there’s a confidence threshold configured and the best score for a query is below that threshold, the category should be 'none'. So for example, 'xyzzy=none'. Same deal in Feature 5.4: if the best classification score is below the configured threshold value, like -4.0, the output must be '<query>=none' rather than returning some weak category anyway. If the query meets or exceeds the threshold, it should output the matched category name normally.

And on the semantic index piece, yes, recategorizing documents is supposed to work in place without forcing a rebuild. The output should include 'needs_rebuild=no' to make that explicit, and after the recategorization happens, subsequent classifications should reflect the updated category assignments immediately.