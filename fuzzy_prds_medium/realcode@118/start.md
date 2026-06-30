## Product Requirement Document

Hey team, we need to wrap up the local storage abstraction library before the sprint ends. The basic idea is that we want developers to be able to stash stuff like user preferences, session tokens, and app config objects without having to manually handle serialization every single time. Think of it like that settings persistence layer we built for the onboarding flow — same vibe but more generalized and reusable across products.

A few things that came up in the last retro: some legacy data in the wild isn't cleanly formatted, so we need to make sure reads don't blow up on that. Also the ops team wants to be able to hook into writes to do auditing — and apparently they sometimes need to be able to block a write from going through entirely, so there needs to be some kind of intercept mechanism.

We also got a complaint that storing empty or blank keys causes silent weirdness downstream, so that needs to be handled properly with a clear error signal. Same deal for trying to store a null raw string — that should also fail loudly with something descriptive.

Should support both sync and async call styles since different parts of the platform use different patterns. The underlying storage backend should be swappable so QA can test without touching real browser storage. Make sure the design doesn't end up as one giant file — separate concerns cleanly.

One quick follow-up from the questions that came in: every keyed call needs to treat key validation the same way, so set, get, get_string, set_string, remove, contains, and key-by-index all need to reject a key if it’s null, empty string, or whitespace-only. When that happens, report it as a normalized error exactly like error=argument_null param=key, and don’t touch the store at all.

Also for the verbatim string write path, set_string / SetItemAsStringAsync needs its own explicit guard for a null data value. That should fail as error=argument_null param=data, and again nothing should be written.

On the structure side, the text storage piece needs to stay behind an interface like IStorageProvider, with the service layer depending on that abstraction instead of a concrete backend. We need to be able to swap in an in-memory backend in place of something platform-specific like browser localStorage so unit tests can run without real browser storage. Same idea for the core domain layer too: keep the IStorageService / ISyncStorageService abstraction in place for the typed get/set behavior with JSON serialization, mirroring the pattern described in Feature 1 of start.md.

For object values, type: object should serialize to compact JSON with no extra whitespace, and property order has to stay in the same order the fields came in. So if the input fields are Id then Name, the stored/rendered form should be exactly {"Id":2,"Name":"Jane Smith"}. That exact string is what get_string should return, and it’s also what get with type object should render as the value.

On the write hook, the pre-save event needs to expose the key being written, the previous stored value, the incoming new value, and a cancel flag that starts false. If the key is new, the old value should come through as <null>. The event line format should be exactly event=changing key=<key> old=<old|<null>> new=<new|<null>> cancel=<true|false>. If a subscriber flips cancel to true, the write is abandoned completely — value is NOT stored, count stays the same, and there is no post-save changed event after that. In that case the only thing emitted is the changing line.

And one backward-compatibility detail to make sure we don’t regress: for Feature 2.2, if stored content isn’t valid JSON, GetItemAsync<string> should return the raw stored text unchanged instead of throwing on deserialization.