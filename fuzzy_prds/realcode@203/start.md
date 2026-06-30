## Product Requirement Document

Hey team, following up on the proxy router project. We've had a few complaints from ops lately — mainly around deployments causing brief outages and some confusion about how traffic gets handled when backends aren't ready yet. We want to tighten this up.

The big thing is: we need the router to be smarter about accepting new backends. Like, it shouldn't just blindly start sending traffic to something that isn't actually responding correctly yet. There should be some kind of window where we verify it's healthy first — similar to how we handled readiness in that gateway module a while back.

Also, we've been getting reports of weird behavior when two teams accidentally register their services on the same hostname. Right now it's unclear what wins and users get inconsistent responses. We need deterministic behavior there.

On the security side, some services are supposed to be HTTPS-only but plaintext requests are sneaking through. We need proper enforcement — and there's a known edge case with certain host patterns that certificate automation can't handle, so that combo should be blocked at registration time.

Finally, the on-call team wants operational controls — ability to hold traffic briefly during a maintenance window, then release it, and a clean shutdown mode that doesn't just drop everything. The timeout values for these holding periods need to be configurable per operation. Let's get this scoped out properly.