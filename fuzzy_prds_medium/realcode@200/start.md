## Product Requirement Document

Hey team, we need to build out that password strength checker library we've been talking about. Basically devs should be able to throw a password at it and get back useful info — how strong it is, roughly how long it'd take to crack, a human-readable label for that time, and some kind of score. We also want it to spit out what patterns it found inside the password (like if someone used a keyboard row, or repeated chars, or a dictionary word). Oh and we need feedback messages too — like warnings and suggestions — similar to what we did in that scoring module a while back, you know the one.

One thing that's been causing support tickets: users are picking passwords that look complex but are actually things like their name or pet — so we need to support passing in personal terms so those get flagged as weak too. There should also be a way to register your own word lists once and reuse them across multiple checks without re-registering every time.

Output should be plain text key=value lines, not JSON. Multiple results should be separated somehow. Numbers need to be rounded consistently — I think to 3 decimal places? Check how we handled that before. Also make sure weird or invalid inputs don't blow things up. Architecture should be clean and modular, not one giant file. Let's get this scoped out properly.

Quick follow-up after the questions that came in. For multiple password evaluations, the output needs to stay as plain key=value blocks, with each password block separated by a line containing exactly `---`. The first line of each block is `password=<the_password_being_evaluated>` and then the rest of that password’s full strength summary follows. Also, there is no trailing `---` after the last block.

On the personal-terms vs reusable-lists thing, the split is: Feature 1.2 `user_terms` are per-request personal terms injected for a single evaluation call, while Feature 1.3 `word_lists` are named lists registered once on an evaluator instance and applied to all subsequent `passwords` in that same request. The word list name, like 'custom', is the dictionary name. For feature 1.3 specifically, the output starts with `password=<list_name>\n` and then immediately `password=<evaluated_password>\n` before the full summary.

For rounding, yes, entropy values are rounded to 3 decimal places and crack time seconds are also rounded to 3 decimal places. Use Ruby's `.round(3)` and strip unnecessary trailing zeros when formatting, so 26.440 displays as 26.44. Same idea for the examples we talked about: 2037200406.475 stays as-is, 4551.454 stays as-is, and zero is expressed as 0.0.

Also, if the password is missing, null, or empty, just treat it as the empty string `""` for evaluation. It should not raise an error. In that case the summary should come back with entropy=0.0, crack_time=0.0, crack_time_display=instant, and score=0.

One other detail for matching: only string (text) entries in `user_terms` or custom `word_lists` should participate. Non-string entries like integers, nulls, booleans, and objects are silently ignored and shouldn’t cause errors. Emoji and Unicode strings are valid text entries and should be treated as dictionary words.

And for the actual score/crack-time behavior, we should align with the zxcvbn reference scoring and crack-time estimation logic, specifically the entropy-to-crack-time conversion and score thresholds defined in the core estimator module (`src/scoring.rb` or equivalent), which maps entropy bits to seconds assuming 10 guesses/second online attack rate.