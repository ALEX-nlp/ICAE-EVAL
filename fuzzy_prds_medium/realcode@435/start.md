## Product Requirement Document

Hey team, we need to build out the form rendering helper for the Bootstrap UI project. Basically the idea is that devs shouldn't have to hand-write all that repetitive Bootstrap form markup every time — labels, inputs, wrappers, error states, the whole thing. We want something where you describe your data entity once and the library spits out the right HTML.

The big thing we keep getting burned on is consistency — missing aria stuff, wrong classes on error states, that kind of thing. We also need it to handle those input group decorators (you know, the prefix/suffix icons and buttons), and it should compose nicely with the validation error display we discussed. There's also that alignment/layout stuff — inline, horizontal, the grid column config — make sure invalid alignment values fail gracefully like we do elsewhere in the codebase, don't just silently produce garbage markup.

Also, please follow the same attribute ordering convention we settled on for the HTML output — check how the existing control renderers do it. And the feedback tooltip mode needs to work alongside the positioning context thing, similar to how we handled it in the label suppression feature.

One more thing: the spacing utility on form groups needs to be configurable at multiple levels (global default, per-form, per-control), and disabling it should remove the class entirely. Make sure closing a form resets any form-level overrides so the next form doesn't inherit them.

A couple follow-ups from the questions that came in. On the HTML output, we do need to be strict here: within every HTML start tag, attributes must be sorted alphabetically by attribute name, same as the Output contract & normalization section of start.md. So yes, that means things like aria-required before class before id before name before type, and boolean/marker attributes should be written in doubled form like required="required".

On the bad alignment case, if someone passes an unsupported value like 'foo', the adapter should output exactly error=invalid_alignment\n and stop there. No exception, no half-rendered form markup.

For input type behavior, the type is inferred from the field name and/or declared data type. A field named 'password' always renders as type='password'. Integer fields render as type='number'. Boolean fields render as a checkbox group (hidden input + checkbox). Text/string fields default to type='text'. Also calling this out because it came up specifically: a field named 'password' is not required by default unless explicitly flagged.

ARIA handling is a little more flexible than the original note made it sound. Per control, 'aria-required': false suppresses that attribute, 'aria-invalid': false suppresses it, and 'aria-describedby': 'custom' replaces the auto-generated value. Hidden-type inputs never receive any ARIA attributes regardless of error/required state.

On templates, opening the form with a 'templates' option should load a named external template set that overrides the default markup templates, so for example custom_templates can add an extra wrapper class. Separately, config can have a 'templateSet' with inline template fragment overrides keyed by layout, like templateSet.horizontal.checkboxFormGroup for the horizontal checkbox group template. Template placeholders use %s for class strings and {{input}}/{{label}}/{{error}}/{{help}} tokens.

For actions/buttons, the 'button' op renders a <button> element with classes 'btn btn-secondary' by default. If a class option like 'success' is passed, translate that to 'btn-success' and put it before 'btn'. The 'submit' op is different: it renders an <input type='submit'> wrapped in <div class='submit'>, and classes should merge from either a space-separated string or a list, with 'btn-secondary' appended automatically.

For the reference entity, 'article' has fields: id (integer), author_id (nullable integer), title (nullable string), body (text), published (boolean, default off). By default, author_id and title are flagged required. For a new entity, the form action should resolve to '/articles/add'. Also, the 'article' op with set/unset can modify schema, required flags, or error state before create.

On required fields, the input itself must carry aria-required="true", required="required", data-validity-message="This field cannot be left empty", oninput="this.setCustomValidity('')", and oninvalid="this.setCustomValidity(''); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)". The wrapper div should also get a 'required' class. And keep the escaping exact in inline JS, so apostrophes are entity-escaped as &#039;.

Last thing, on the tooltip/label behavior: Feature 5.1 still applies here. When label=false, the label element is omitted entirely from the control group, and that still needs to work correctly with tooltip feedback and the positioning context.