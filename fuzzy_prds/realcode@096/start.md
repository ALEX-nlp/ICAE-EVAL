## Product Requirement Document

Hey team, we need to build out this text classification and semantic search toolkit that's been on the backlog. The core idea is developers drop in plain text and get back useful signals — categories, scores, ranked docs, that kind of thing. We had a similar pipeline in the old recommendation engine (you can probably grep around for how we handled the scoring edge cases there), so let's not reinvent the wheel too much.

Main things I care about: the tokenizer needs to be smart about what it keeps vs throws away depending on config, the Bayes classifier should handle the case where someone queries something totally foreign to the training data (users have been complaining the old one just confidently returns garbage instead of saying 'I don't know'), and the semantic index piece needs to stay usable even after someone reorganizes which documents belong to which bucket — without having to blow everything away and start over.

Also there's been a recurring complaint that when people index a document that's basically just filler words, the system silently accepts it and then behaves weirdly downstream. We want a clear signal when that happens.

One more thing — the serialization story needs to actually work end to end. Someone on the data team tried to save and reload an index last sprint and the rankings came back different. That's a blocker.

Let's make sure the output format is consistent and deterministic across all these features. cc @backend-platform