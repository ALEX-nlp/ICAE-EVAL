## Product Requirement Document

Hey team, we need to build out that auto-loading library thing we talked about last sprint. Basically the idea is that developers shouldn't have to write a bunch of require statements by hand — the system should just figure out what file maps to what constant name based on where the file lives. Like if you have a file called `users_controller.rb` it should just know that maps to `UsersController` without anyone telling it explicitly.

We also need it to handle the nested folder situation — same pattern we used for the namespace resolution in that old config module, you know the one. Directories should act as namespaces automatically.

There's also the reload story — in development people want to be able to change a file and have it pick up the new version without restarting. But we should make sure that only works if someone explicitly opts into it, otherwise it should blow up with a clear error.

Oh and the gem versioning edge case — someone brought this up in the thread — when it's the top-level version file directly under the package namespace it should behave differently than a nested one. Ask around if you're not sure what I mean by that.

Ignored paths, eager loading, duplicate root handling — all the usual stuff. Make sure stale constants get cleaned up properly on unload. Error messages need to be consistent and machine-readable.