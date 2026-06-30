## Product Requirement Document

Hey team, we need to wrap up the coupon redemption library before next sprint. The core idea is pretty straightforward — developers should be able to plug this into their apps and get coupon creation, checking, and redemption without writing all the boilerplate themselves. Think of it like the voucher module we shipped for the loyalty project last year, same kind of vibe but more flexible.

Main things we care about: coupons should track whether they've been used up or expired, and there should be some way to lock a coupon to a specific buyer or buyer category so it can't just be used by anyone. We also need to handle the case where a coupon is being applied to something on behalf of someone else — like a gift or enrollment scenario.

On the limits side, we need both a per-person cap and a global stock cap, and when either one runs out the system should say so clearly rather than just blowing up. There's also a bulk generation flow for seeding campaigns — marketing keeps asking about this.

Optional/nullable coupon fields should degrade gracefully — no crashes if someone passes nothing. And coupons should be able to carry extra payload data for downstream job triggers or whatever the app needs.

Finally, the storage layer needs to support alternate table configurations, similar to how we handled the multi-tenant setup before. Let me know if anything's unclear.