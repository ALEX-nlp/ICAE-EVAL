## Product Requirement Document

Hey team, we need to build out a fluent builder toolkit for our Places SDK wrapper. Basically devs keep complaining that constructing place objects and service request objects is super tedious and error-prone — they have to remember which fields are required vs optional every single time, and the boilerplate is everywhere. We want a single clean entry point per object type where you pass in the required stuff upfront and then configure anything optional in one trailing block.

There are two main groups of things to build: the data model side (photos, plus codes, address stuff, places, opening hours, predictions) and the service request side (fetch place, fetch photo, find current place, autocomplete, text search). The request objects also need to support cancellation — similar to how we handled it in that token-lifecycle pattern from the last SDK module — where you can prove the request is actually holding a live handle and not just a snapshot.

Also important: the codebase needs to be structured cleanly with the JSON adapter stuff kept totally separate from the core builder logic. No leaking of output/formatting concerns into the domain layer. We want this to be extensible so adding new object types later doesn't require touching existing code.

For location biasing on some requests you can do either a box (two corners) or a circle (center + distance). Price levels on text search have a specific internal integer mapping we need to handle correctly. Ping me if anything is unclear.