## Product Requirement Document

Hey team, we need to wrap up that record-mapping library we've been discussing. The core idea is that devs are sick of writing the same boilerplate row-mapping and relationship-stitching code over and over — it's causing those N+1 read issues we keep seeing in prod and the error messages are all over the place depending on who wrote the query. We basically need something like what we did with the loader abstraction in the billing module, but more general-purpose.

The library should let you pull back lightweight records with just the fields you care about, handle related data (both direct and the multi-hop stuff), and support batching so we're not blowing up memory on big result sets. Raw SQL should still work for the cases where people need it. Projections to scalar arrays would be a nice-to-have too.

One thing that keeps biting us — when a field wasn't selected or a relationship wasn't loaded, the error that comes back is totally inconsistent. We need stable, predictable errors that don't leak internal stack details.

Also there was some discussion about polymorphic targets (where the related record could come from different tables per row) and indirect traversal paths — both need to work. Output should be deterministic JSON on stdout. Ask me if anything's unclear, but I think the test files cover most of the edge cases.