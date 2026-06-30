## Product Requirement Document

Hey team, we need to get the Marpit slide renderer wired up properly. Basically authors are writing their decks in Markdown and we need to turn that into proper HTML + CSS output. The core thing is splitting markdown into slides, handling those presenter-only notes (you know, the ones that shouldn't show up on screen), and making sure all the metadata stuff propagates correctly across slides like we discussed in the planning session.

Also there's the image handling — people want to do things like set background images and resize stuff inline using that alt-text trick, similar to how the image pipeline in the old asset module works. We need that supported.

On the CSS side, we need themes to be packaged up correctly — imports rolled up, scoped styles handled, and print rules included. The inline SVG wrapping mode also needs to work when enabled, and the section selectors need to be rewritten accordingly for that mode.

One more thing: the heading-based slide splitting needs to respect both numeric and array configs, and there's a directive override from within the document itself that should take priority. The header/footer repeat behavior also needs to work — inline markdown inside those values should render properly.

Let's make sure the output format matches exactly what downstream consumers expect. There are some edge cases around empty docs and code blocks that we got burned by before — make sure those are covered.