## Product Requirement Document

Hey team, we need to get the Marpit slide renderer wired up properly. Basically authors are writing their decks in Markdown and we need to turn that into proper HTML + CSS output. The core thing is splitting markdown into slides, handling those presenter-only notes (you know, the ones that shouldn't show up on screen), and making sure all the metadata stuff propagates correctly across slides like we discussed in the planning session.

Also there's the image handling — people want to do things like set background images and resize stuff inline using that alt-text trick, similar to how the image pipeline in the old asset module works. We need that supported.

On the CSS side, we need themes to be packaged up correctly — imports rolled up, scoped styles handled, and print rules included. The inline SVG wrapping mode also needs to work when enabled, and the section selectors need to be rewritten accordingly for that mode.

One more thing: the heading-based slide splitting needs to respect both numeric and array configs, and there's a directive override from within the document itself that should take priority. The header/footer repeat behavior also needs to work — inline markdown inside those values should render properly.

Let's make sure the output format matches exactly what downstream consumers expect. There are some edge cases around empty docs and code blocks that we got burned by before — make sure those are covered.

Quick follow-up from the questions that came in. For empty input, we still need to emit a real deck shape, not nothing — an empty Markdown string must still produce exactly one slide section. The output HTML should be `<div class="marpit"><section id="1"></section>
</div>` and comments should be `[[]]`. Never return zero slides for an empty input.

Also, on the presenter note extraction, we only want to pull HTML comments when they’re actually part of normal prose or heading content. If someone puts HTML comments inside fenced code blocks or inline code spans, those must NOT be extracted as presenter comments. They stay as literal code text in the rendered HTML.

On the array response behavior, when array output is requested, the renderer returns one HTML fragment string per slide instead of a single combined string. The `html_is_array` flag in output is `true` and `html_item_count` equals the number of slides. Each array item contains the markup for exactly one `<section>`. The wrapper `<div class="marpit">` is NOT included per-item in array mode.

A couple metadata specifics too. In loose YAML mode, color-like values like `#fff` that strict YAML would reject are accepted as unquoted strings in front matter and directive comments. Strict mode (default) still requires proper YAML quoting for those, and the mode is configurable per render call. For directive propagation, anything prefixed with an underscore like `_class` applies ONLY to the slide where it’s defined. Non-prefixed local directives like `class` apply to that slide AND all subsequent slides. Global/deck-wide directives like `theme` propagate to all slides regardless of position.

For heading splitting, `headingDivider` can be either a number or an array of numbers. With a number, split at that level and above. With an array of numbers, split only at exactly those heading levels. If it’s `false` or an invalid value, don’t do heading-based splitting at all and keep everything on one slide. And yes, a document-level directive inside the Markdown can still override the programmatic setting.

Last bit on images since there were a few follow-ups there: image alt text is parsed for space-separated keyword tokens like `w:100`, `h:200`, `bg`, and color-like strings. Those tokens are control data, so they drive inline style, background directives, or text color instead of showing up as visible alt text. Same idea as the Marpit image plugin parsing logic for width (`w:`), height (`h:`), background keyword (`bg`), and color shorthand, converting them to CSS inline styles or slide-level directives. See feature6_images_and_backgrounds.json test cases.