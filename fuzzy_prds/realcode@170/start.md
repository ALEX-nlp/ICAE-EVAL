## Product Requirement Document

Hey team, we need to build out the core backend for our new analytics data collection pipeline. Basically, we're getting hammered with support tickets because our current setup loses visitor identity between page loads, and the ops team can't configure anything without a code deploy. Super frustrating.

The big ask: we need something that tracks visitors with stable IDs that survive cookie round-trips, reads config values safely without blowing up when something's missing (you know how ops always forgets to set every field), maps incoming web hits into clean typed records using a config file instead of hardcoded logic, and writes everything out to files in a way that downstream can trust — i.e., only fully-written files should look 'done'.

For the file writing part, we need two modes: one that just rolls files on a schedule, and one that groups events by 'which time window did this session start in' — similar to how we handled the batching logic in that old session affinity module. If a session started in an earlier window and that file is still open, the event should go there.

One thing I keep forgetting to mention: the config mapping layer needs to loudly reject bad setups early — operators should know immediately if something's misconfigured, not find out hours later from missing data. Please keep all output as plain key=value lines, one per line.