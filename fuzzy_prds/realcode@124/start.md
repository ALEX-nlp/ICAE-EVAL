## Product Requirement Document

Hey team, we've been getting complaints from the platform folks that our deployment configs are a total mess — people keep copy-pasting manifests for every environment and then things drift apart. We need some kind of toolkit that lets you write one config file and have it work across staging, prod, etc. without hand-editing everything each time.

The big thing is there should be a way to pull in values from environment variables and external files inline, kind of like how we did the substitution stuff in the old login module, but smarter — it should catch loops and missing vars before things blow up in prod. Also there needs to be some validation so we know upfront if a resource type even exists on the target cluster or if an API version got removed, instead of finding out at apply time.

For config merging, the rule should be pretty intuitive — shared stuff lives in a common block, and per-environment bits override it. Maps should merge deep, but lists just replace wholesale, no concatenation weirdness.

We also need the template rendering to support some filters like base64 encode/decode and hashing. And there should be tag-based filtering so teams can opt in or out of deploying certain pieces.

Important: this should be a proper multi-file project, not one giant script. Keep the concerns separated cleanly. Oh and the cluster version/deprecation checking should be semantic-version aware.