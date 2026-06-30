## Product Requirement Document

Hey team, we need to wrap up the config + media metadata utility work we discussed in the last sprint. The goal is basically a small library that handles all the annoying boilerplate around reading app settings and dealing with media records. Think of it like that config-merging pattern we used in the old player backend — same idea but cleaner.

On the config side, we need typed setting conversion (strings, secrets, booleans, lists, ports, etc.), the ability to pull settings from multiple sources and merge them, and some way to preserve user comments when we round-trip config files. The secret type needs special handling for display vs raw output — users were complaining that credentials were showing up in logs.

For media stuff, we need immutable record types for artists, albums, tracks, playlists, and queue entries. They should serialize nicely to JSON and support non-destructive updates. There was also a reported bug where artist ordering was causing false 'changed' alerts downstream, so equality checks need to be order-insensitive for those collections.

Also need locale-aware error message decoding (hex-encoded bytes were breaking the error reporter on some EU deployments) and the XDG directory resolver that reads from env vars and falls back to the standard user-dirs config file. Port the fallback logic from how we handled it in the platform utils — you know the one.

Please wire everything up so it reads JSON commands from stdin and writes results to stdout for test harness compatibility.

One more pass on the details the team asked about: for secret config values, if we serialize with display=true the output should be exactly '********' every time, no matter how long the real secret is. That masking only happens when the 'display' flag is true; otherwise we return the raw trimmed string value normally.

For booleans, please accept case-insensitive 'yes', 'true', '1', 'on' as true, and 'no', 'false', '0', 'off' as false. Anything else should produce 'error=invalid_value\n'. Same neutral handling for ports too: they need to be integers in the range 1–65535 inclusive, and anything outside that range like 65536 or 0, plus non-numeric strings, should produce 'error=invalid_value\n' instead of throwing.

On list parsing, split on commas OR newlines, then strip surrounding whitespace from each item. So 'foo, bar ,baz ' becomes ["foo", "bar", "baz"]. For the locale decode path, locale_decode can take either a plain text string or a hex-encoded byte string. If the input has 'encoding': 'hex', decode the hex string to bytes first and then decode that to a Unicode string using the active locale encoding. If there’s no encoding field, just return the value as-is as a plain string passthrough.

A couple media/serialization specifics too. The ref_factory operation should build a lightweight Ref from 'kind', 'name', and 'uri', and when serialized it needs '__model__': 'Ref' with 'kind' mapped onto the output field named 'type'. The example to match is {"__model__": "Ref", "name": "Foo", "type": "album", "uri": "album:foo"}. For tl_track_iter, it takes a queue_item entity with positional=true and returns {"tlid": <int>, "track": <serialized Track>}. The track should use the normal __model__ marker, and tlid needs to stay a raw integer, not a string.

Also, all JSON output should have keys sorted alphabetically, basically sort_keys=True behavior, and that applies both to config_load output and all media entity serialization. '__model__' should come before the alphabetic field names since underscore sorts before letters in ASCII, which is what we want here.

And just to be explicit on the two bigger integration bits people asked about: the config_load behavior in feature2_config_sources.json is merging defaults (INI text snippets), file sources (kind='file'), directory sources (kind='directory', .conf extension filter), and override triples [section, key, value] into a single nested dict. For the XDG resolver in feature8_xdg_directory_resolution.json, when env vars like XDG_CACHE_HOME are absent, fall back to ~/.cache, ~/.config, ~/.local/share, and parse user-dirs.dirs content for user-specific dirs like XDG_MUSIC_DIR.