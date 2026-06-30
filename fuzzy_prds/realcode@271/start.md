## Product Requirement Document

hey team, we need to get the bitcore node container thing wrapped up — the one where you can plug in service modules without having to hand-wire everything. basically the idea is that devs shouldn't need to manually figure out boot order or worry about method name clashes when two services try to register the same thing. there's also the event routing piece where services publish named events and subscribers should get routed automatically without each service reimplementing that logic themselves.

we also need those small utility checks we discussed — the ones for making sure identifiers are well-formed (similar to how we validated hashes in the wallet module last time) and the counter initialization helper that preserves existing values even when they're falsy. the tricky part there is it should care about whether a key *exists*, not whether the value is truthy — we got burned by that before.

the network selection on startup also needs to handle the three environments correctly, including the local regression one that has to be explicitly registered. and the lifecycle — start in dependency order, stop only what actually started, surface errors properly if something fails to boot or if there's a naming collision.

please keep the code split up sensibly, not one giant file. the JSON test harness is just for black-box testing, the real logic should be decoupled from that.