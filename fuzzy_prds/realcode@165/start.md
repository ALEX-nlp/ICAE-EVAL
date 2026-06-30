## Product Requirement Document

Hey team, we need to build out that actor concurrency library we've been talking about. The core idea is that developers should be able to spin up isolated 'systems', put named workers inside them, and have those workers talk to each other via messages without worrying about the plumbing underneath. Think of it like the pattern we used in the notification service refactor last quarter — same isolation idea, but generalized.

A few things I know are important from the stakeholder side: naming has to be strict (we had bugs before from weird characters sneaking into identifiers), parents should know about their kids but not their grandkids, and if something crashes it shouldn't take down the whole world — there should be ways to configure recovery. Also someone mentioned we need a way to 'ask' an actor something and wait for an answer, but it can't wait forever, and the error messages that come back need to be clean, nothing internal leaking out.

We also need lifecycle stuff — actors should be stoppable, stopping a parent should clean up everything below it, and there's some ask about actors that shut themselves down if they've been sitting idle too long. The after-stop situation also needs a callback of some kind so you can inspect what was still pending.

Please make sure the code isn't one giant file — it got messy last time. Reference the structure notes in start.md for how to split things up.