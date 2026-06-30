## Product Requirement Document

Hey team, we need to build out the linked data processing library we discussed in last quarter's planning. Basically we want something that can take JSON-LD documents and do all the standard transformations on them — you know, the usual graph stuff. Think of it like that RDF utility we prototyped for the semantic web client last year, but productionized properly.

The big pain point right now is that every team that touches linked data ends up writing their own one-off scripts to handle IRI resolution, graph flattening, context application, etc. and they always end up with subtle data loss or serialization inconsistencies when exchanging data with external RDF systems. We need one canonical place for all of this.

It should handle the full lifecycle: expanding compact documents, squishing them back down with a context, making the graph structure flat and comparable, reshaping data around a template, converting back and forth to the raw triple format, and producing a stable canonical form. There's also some namespace shortening behavior we need — refer to how we handled prefix compaction in the graph client module — and it needs to report problems cleanly without exposing internal exception noise to callers.

The output format needs to be consistent and pretty-printed in a way that downstream tools can parse reliably. Architecture should be clean, multi-file, separated concerns. Don't make it a god file.