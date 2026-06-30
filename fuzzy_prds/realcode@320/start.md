## Product Requirement Document

Hey team, we need a client adapter thingy for that remote AI service we've been integrating with. Basically devs are complaining they keep writing the same boilerplate over and over just to talk to the service — checking if it's up, grabbing providers, running completions, messing with datasets, submitting jobs, getting model recommendations, etc. It's a mess and everyone's doing it slightly differently which causes bugs.

The idea is to build something that wraps all that up cleanly. There should be a way to run it from the command line where you pipe in some JSON describing what you want and it spits out the result — similar to how we did that stdin/stdout pattern on the billing connector last quarter, you know the one. The output format needs to be consistent key=value lines, one per line.

A few things that keep biting us: when a provider isn't in the supported list we need a clear normalized error (not a stack trace), same for blank prompts. Datasets and jobs have their own create/delete/list flows. Oh and the health check output should always include the deployment field even if the service doesn't send it back. For job types we support evaluate and inference routes. Model suggestions can fail with a bad task name and that needs to be handled gracefully too.

Structure should be clean, not one giant file. Tests should run with a single bash command. Let me know if questions.