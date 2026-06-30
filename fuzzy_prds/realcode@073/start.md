## Product Requirement Document

Hey team, we need to wire up the new image redirection logic for our cluster admission setup. Basically the idea is that when a pod comes in, we want to automatically rewrite its container images so they pull from our internal registry instead of wherever they were originally pointing. This is the same kind of 'transparent swap' pattern we talked about in the infra sync last quarter.

A few things I know we need: there should be some way to configure which pods/containers actually get redirected (not everything should be redirected blindly), and we need to handle the auth side so the mirroring process can actually pull from source registries. Also the system should be resilient — if someone passes in a bad config keyword it shouldn't just blow up, it should degrade gracefully.

One thing I'm not totally sure about is how image names get normalized when they're rewritten — like what happens with images that have both a tag and a digest, or bare names like 'nginx' with no registry prefix. I think there was some prior art in how we handled image references in the old registry-compat module but I don't remember the exact rules.

The output format for the CLI adapter needs to match what the test harness expects, so please check the existing test cases carefully. Let me know if anything is unclear — I'll try to get back to you same day.