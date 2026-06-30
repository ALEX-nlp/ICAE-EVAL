## Product Requirement Document

Hey team, we need a small utility that takes a deployment descriptor and spits out a list of parameter sets we can feed into our templating pipeline. Basically, there are three ways someone might describe where deployments come from: they either hand-write a short list, point at a folder structure, or reference some config files sitting in the repo. The tool needs to handle all three cases and produce consistent, ordered output every time — no more each squad inventing their own discovery logic and getting different results.

The output format should be something the CI scripts can parse easily, similar to what the infra team settled on for that config-flattening work we did on the cluster-registration flow a while back. You'll know it when you see it — basically a count line up top, then numbered blocks.

One important thing: when the underlying data source is unavailable or broken, we absolutely cannot silently return empty results. The tool has to loudly signal that something went wrong instead of letting a half-baked deployment sneak through.

Also, the folder-scanning mode has some subtlety around how wildcards work with nested paths — make sure the matching logic doesn't accidentally pick up things two levels deep when you only asked for one level. And for config files, nested JSON keys need to be collapsed in a specific way. Please keep the I/O plumbing totally separate from the core logic so we can unit-test it properly without needing a real repo.