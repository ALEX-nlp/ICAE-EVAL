## Product Requirement Document

# Server-Side HTML/XML Document Manipulation Engine

## Project Goal

Build a server-side engine that loads an HTML or XML markup string into an
in-memory document tree and exposes a concise, chainable API for querying and
transforming that tree. The engine must let callers select nodes with CSS
selectors, read and mutate attributes, properties, classes, inline styles and
form-control values, traverse the tree in every direction, restructure the DOM,
serialize any subtree back to markup, and serialize forms to query strings — all
without a browser.

## Background & Problem

Programs that scrape, template, or post-process web content need to manipulate
markup the way a browser does, but in a headless environment. A full browser DOM
is far too heavy for this, while naive string/regex editing is fragile and cannot
honor the HTML parsing algorithm (implicit `<tbody>`, auto-closed tags, raw-text
elements, entity decoding, and so on).

This project specifies a lightweight engine that parses markup into a real node
tree and offers a familiar, chainable fluent interface over it. The engine
supports two parsing/serialization modes: a forgiving HTML mode that lower-cases
tag names and repairs malformed structure, and a strict XML mode that preserves
case and self-closes empty elements.

## Architecture & Engineering Constraints

The reference harness drives your implementation as a black box over a
line-oriented protocol:

- The program reads a **single JSON command object from stdin** and writes a
  **plain-text result to stdout**. No other output may go to stdout.
- The command object has these fields:

  | field | meaning |
  | --- | --- |
  | `document` | the markup string to load (a non-string is an input error) |
  | `options` | load options; `{ "xml": true }` selects strict XML mode |
  | `fragment` | when `true`, load as a fragment without document scaffolding |
  | `select` | a CSS selector for the working set; `"@document"` targets the whole document |
  | `within` | [a dynamic insertion point based on show options] context selector that scopes `select` |
  | `op` | the operation to perform (see Core Features) |
  | `args` | operation parameters |
  | `show` | how to render the result: `{ "select": ..., "as": ..., "name": ... }` |

- The `show.as` render kinds are: `outer` (outer markup), `inner` (inner markup),
  `text` (decoded text), `count` (number of matched nodes), `classes` (the
  `class` attribute per matched node, newline-joined), `attr`/`prop` (one named
  attribute or property), `val` (a control value; multi-values joined by commas),
  and `tagnames`. A missing attribute/value renders as `(null)`, an absent value
  as `(undefined)`.
- Read operations (`text`, `count`, `outer`, `inner`, `attr`, `val`, `data`,
  `serialize`, `serialize_array`, `css`, `has_class`, `is`, `index`) return their
  result directly.
- **Error handling (language-neutral):** any failure must render as a single line
  `error=<category>` with no stack trace or runtime-specific text. Categories:
  `invalid_input` (e.g. the document is not a string) and `invalid_selector`
  (an unparseable selector).
- Output must be **deterministic** and depend only on the input command.

## Core Features

### Feature 1: Element selection

#### 1.1 Select elements by class, id, tag and report match counts and content

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": ".apple",
  "op": "text"
}
```
Expected output:
```
Apple
```

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": "li",
  "op": "count"
}
```
Expected output:
```
3
```

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": ".notthere",
  "op": "count"
}
```
Expected output:
```
0
```

#### 1.2 Restrict a selector to a given context subtree

Input:
```json
{
  "document": "<ul id=\"food\"><ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul><ul id=\"vegetables\"><li class=\"carrot\">Carrot</li><li class=\"sweetcorn\">Sweetcorn</li></ul></ul>",
  "select": ".apple",
  "within": "#fruits",
  "op": "text"
}
```
Expected output:
```
Apple
```

#### 1.3 Attribute substring and sibling combinator selectors

Input:
```json
{
  "document": "<ul id=\"drinks\"><li class=\"beer\">Beer</li><li class=\"juice\">Juice</li><li class=\"milk\">Milk</li><li class=\"water\">Water</li><li class=\"cider\">Cider</li></ul>",
  "select": ".beer + li",
  "op": "text"
}
```
Expected output:
```
Juice
```

Input:
```json
{
  "document": "<ul id=\"chocolates\"><li class=\"linth\" data-highlight=\"Lindor\" data-origin=\"swiss\">Linth</li><li class=\"frey\" data-taste=\"sweet\" data-best-collection=\"Mahony\">Frey</li><li class=\"cailler\">Cailler</li></ul>",
  "select": "[class*=\"ill\"]",
  "op": "text"
}
```
Expected output:
```
Cailler
```

### Feature 2: Attributes and properties

#### 2.1 Read and write element attributes; null removes an attribute

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": ".apple",
  "op": "attr",
  "args": {
    "name": "class"
  }
}
```
Expected output:
```
apple
```

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": ".apple",
  "op": "set_attr",
  "args": {
    "name": "data-x",
    "value": "y"
  },
  "show": {
    "as": "outer"
  }
}
```
Expected output:
```
<li class="apple" data-x="y">Apple</li>
```

#### 2.2 Remove one or more space-separated attributes

Input:
```json
{
  "document": "<div id=\"a\" class=\"b\" data-z=\"z\"></div>",
  "fragment": true,
  "select": "div",
  "op": "remove_attr",
  "args": {
    "name": "class"
  },
  "show": {
    "as": "outer"
  }
}
```
Expected output:
```
<div id="a" data-z="z"></div>
```

#### 2.3 Read element properties: tagName, checked, outerHTML

Input:
```json
{
  "document": "<input type=\"checkbox\" checked>",
  "fragment": true,
  "select": "input",
  "op": "prop",
  "args": {
    "name": "checked"
  }
}
```
Expected output:
```
true
```

#### 2.4 Parse data-* attributes with type coercion

Input:
```json
{
  "document": "<ul id=\"chocolates\"><li class=\"linth\" data-highlight=\"Lindor\" data-origin=\"swiss\">Linth</li><li class=\"frey\" data-taste=\"sweet\" data-best-collection=\"Mahony\">Frey</li><li class=\"cailler\">Cailler</li></ul>",
  "select": ".linth",
  "op": "data",
  "args": {
    "name": "highlight"
  }
}
```
Expected output:
```
type=string
value="Lindor"
```

Input:
```json
{
  "document": "<ul id=\"chocolates\"><li class=\"linth\" data-highlight=\"Lindor\" data-origin=\"swiss\">Linth</li><li class=\"frey\" data-taste=\"sweet\" data-best-collection=\"Mahony\">Frey</li><li class=\"cailler\">Cailler</li></ul>",
  "select": ".frey",
  "op": "data",
  "args": {
    "name": "bestCollection"
  }
}
```
Expected output:
```
type=string
value="Mahony"
```

Input:
```json
{
  "document": "<div data-n=\"42\"></div>",
  "fragment": true,
  "select": "div",
  "op": "data",
  "args": {
    "name": "n"
  }
}
```
Expected output:
```
type=number
value=42
```

Input:
```json
{
  "document": "<div data-e=\"1E10\"></div>",
  "fragment": true,
  "select": "div",
  "op": "data",
  "args": {
    "name": "e"
  }
}
```
Expected output:
```
type=string
value="1E10"
```

### Feature 3: Form-control values

#### 3.1 Read the value of selects, text inputs and multi-selects

Input:
```json
{
  "document": "<select id=\"one\"><option value=\"option_not_selected\">Option not selected</option><option value=\"option_selected\" selected>Option selected</option></select><select id=\"one-valueless\"><option>Option not selected</option><option selected>Option selected</option></select><select id=\"one-html-entity\"><option>Option not selected</option><option selected>Option &lt;selected&gt;</option></select><select id=\"one-nested\"><option>Option not selected</option><option selected>Option <span>selected</span></option></select><input type=\"text\" value=\"input_text\" /><input type=\"checkbox\" name=\"checkbox_off\" value=\"off\" /><input type=\"checkbox\" name=\"checkbox_on\" value=\"on\" checked /><input type=\"checkbox\" name=\"checkbox_valueless\" /><input type=\"radio\" value=\"off\" name=\"radio\" /><input type=\"radio\" name=\"radio\" value=\"on\" checked /><input type=\"radio\" value=\"off\" name=\"radio[brackets]\" /><input type=\"radio\" name=\"radio[brackets]\" value=\"on\" checked /><input type=\"radio\" name=\"radio_valueless\" /><select id=\"multi\" multiple><option value=\"1\">1</option><option value=\"2\" selected>2</option><option value=\"3\" selected>3</option><option value=\"4\">4</option></select><select id=\"multi-valueless\" multiple><option>1</option><option selected>2</option><option selected>3</option><option>4</option></select>",
  "select": "#one",
  "op": "val"
}
```
Expected output:
```
option_selected
```

Input:
```json
{
  "document": "<select id=\"one\"><option value=\"option_not_selected\">Option not selected</option><option value=\"option_selected\" selected>Option selected</option></select><select id=\"one-valueless\"><option>Option not selected</option><option selected>Option selected</option></select><select id=\"one-html-entity\"><option>Option not selected</option><option selected>Option &lt;selected&gt;</option></select><select id=\"one-nested\"><option>Option not selected</option><option selected>Option <span>selected</span></option></select><input type=\"text\" value=\"input_text\" /><input type=\"checkbox\" name=\"checkbox_off\" value=\"off\" /><input type=\"checkbox\" name=\"checkbox_on\" value=\"on\" checked /><input type=\"checkbox\" name=\"checkbox_valueless\" /><input type=\"radio\" value=\"off\" name=\"radio\" /><input type=\"radio\" name=\"radio\" value=\"on\" checked /><input type=\"radio\" value=\"off\" name=\"radio[brackets]\" /><input type=\"radio\" name=\"radio[brackets]\" value=\"on\" checked /><input type=\"radio\" name=\"radio_valueless\" /><select id=\"multi\" multiple><option value=\"1\">1</option><option value=\"2\" selected>2</option><option value=\"3\" selected>3</option><option value=\"4\">4</option></select><select id=\"multi-valueless\" multiple><option>1</option><option selected>2</option><option selected>3</option><option>4</option></select>",
  "select": "select#multi",
  "op": "val"
}
```
Expected output:
```
2,3
```

#### 3.2 Set the value of a text input and read it back

Input:
```json
{
  "document": "<select id=\"one\"><option value=\"option_not_selected\">Option not selected</option><option value=\"option_selected\" selected>Option selected</option></select><select id=\"one-valueless\"><option>Option not selected</option><option selected>Option selected</option></select><select id=\"one-html-entity\"><option>Option not selected</option><option selected>Option &lt;selected&gt;</option></select><select id=\"one-nested\"><option>Option not selected</option><option selected>Option <span>selected</span></option></select><input type=\"text\" value=\"input_text\" /><input type=\"checkbox\" name=\"checkbox_off\" value=\"off\" /><input type=\"checkbox\" name=\"checkbox_on\" value=\"on\" checked /><input type=\"checkbox\" name=\"checkbox_valueless\" /><input type=\"radio\" value=\"off\" name=\"radio\" /><input type=\"radio\" name=\"radio\" value=\"on\" checked /><input type=\"radio\" value=\"off\" name=\"radio[brackets]\" /><input type=\"radio\" name=\"radio[brackets]\" value=\"on\" checked /><input type=\"radio\" name=\"radio_valueless\" /><select id=\"multi\" multiple><option value=\"1\">1</option><option value=\"2\" selected>2</option><option value=\"3\" selected>3</option><option value=\"4\">4</option></select><select id=\"multi-valueless\" multiple><option>1</option><option selected>2</option><option selected>3</option><option>4</option></select>",
  "select": "input[type=\"text\"]",
  "op": "set_val",
  "args": {
    "value": "changed"
  },
  "show": {
    "as": "val"
  }
}
```
Expected output:
```
changed
```

### Feature 4: Class manipulation

#### 4.1 Test whether the selection carries a class

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": ".apple",
  "op": "has_class",
  "args": {
    "name": "apple"
  }
}
```
Expected output:
```
class=apple
hasClass=true
```

#### 4.2 Add, remove and toggle class tokens

Input:
```json
{
  "document": "<div class=\"a\"></div>",
  "fragment": true,
  "select": "div",
  "op": "add_class",
  "args": {
    "value": "b c"
  },
  "show": {
    "as": "classes"
  }
}
```
Expected output:
```
a b c
```

Input:
```json
{
  "document": "<div class=\"a b c\"></div>",
  "fragment": true,
  "select": "div",
  "op": "remove_class",
  "args": {
    "value": "b"
  },
  "show": {
    "as": "classes"
  }
}
```
Expected output:
```
a c
```

### Feature 5: Inline style declarations

#### 5.1 Read inline style declarations

Input:
```json
{
  "document": "<li style=\"hai: there\">x</li>",
  "fragment": true,
  "select": "li",
  "op": "css",
  "args": {
    "name": "hai"
  }
}
```
Expected output:
```
there
```

Input:
```json
{
  "document": "<li style=\"margin: 0; color: red\">x</li>",
  "fragment": true,
  "select": "li",
  "op": "css",
  "args": {
    "name": [
      "margin",
      "color"
    ]
  }
}
```
Expected output:
```
margin=0
color=red
```

#### 5.2 Write inline style declarations and serialize them

Input:
```json
{
  "document": "<li>x</li>",
  "fragment": true,
  "select": "li",
  "op": "set_css",
  "args": {
    "name": "margin",
    "value": "0"
  },
  "show": {
    "as": "attr",
    "name": "style"
  }
}
```
Expected output:
```
margin: 0;
```

### Feature 6: Form serialization

#### 6.1 URL-encode form controls into a query string

Input:
```json
{
  "document": "<form id=\"simple\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /></form><form id=\"nested\"><div><input type=\"text\" name=\"fruit\" value=\"Apple\" /></div><input type=\"text\" name=\"vegetable\" value=\"Carrot\" /></form><form id=\"disabled\"><input type=\"text\" name=\"fruit\" value=\"Apple\" disabled /></form><form id=\"submit\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /><input type=\"submit\" name=\"submit\" value=\"Submit\" /></form><form id=\"select\"><select name=\"fruit\"><option value=\"Apple\">Apple</option><option value=\"Orange\" selected>Orange</option></select></form><form id=\"unnamed\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /><input type=\"text\" value=\"Carrot\" /></form><form id=\"multiple\"><select name=\"fruit\" multiple><option value=\"Apple\" selected>Apple</option><option value=\"Orange\" selected>Orange</option><option value=\"Carrot\">Carrot</option></select></form><form id=\"textarea\"><textarea name=\"fruits\">Apple\nOrange</textarea></form><form id=\"spaces\"><input type=\"text\" name=\"fruit\" value=\"Blood orange\" /></form>",
  "select": "#simple",
  "op": "serialize"
}
```
Expected output:
```
fruit=Apple
```

Input:
```json
{
  "document": "<form id=\"simple\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /></form><form id=\"nested\"><div><input type=\"text\" name=\"fruit\" value=\"Apple\" /></div><input type=\"text\" name=\"vegetable\" value=\"Carrot\" /></form><form id=\"disabled\"><input type=\"text\" name=\"fruit\" value=\"Apple\" disabled /></form><form id=\"submit\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /><input type=\"submit\" name=\"submit\" value=\"Submit\" /></form><form id=\"select\"><select name=\"fruit\"><option value=\"Apple\">Apple</option><option value=\"Orange\" selected>Orange</option></select></form><form id=\"unnamed\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /><input type=\"text\" value=\"Carrot\" /></form><form id=\"multiple\"><select name=\"fruit\" multiple><option value=\"Apple\" selected>Apple</option><option value=\"Orange\" selected>Orange</option><option value=\"Carrot\">Carrot</option></select></form><form id=\"textarea\"><textarea name=\"fruits\">Apple\nOrange</textarea></form><form id=\"spaces\"><input type=\"text\" name=\"fruit\" value=\"Blood orange\" /></form>",
  "select": "#nested",
  "op": "serialize"
}
```
Expected output:
```
fruit=Apple&vegetable=Carrot
```

Input:
```json
{
  "document": "<form id=\"simple\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /></form><form id=\"nested\"><div><input type=\"text\" name=\"fruit\" value=\"Apple\" /></div><input type=\"text\" name=\"vegetable\" value=\"Carrot\" /></form><form id=\"disabled\"><input type=\"text\" name=\"fruit\" value=\"Apple\" disabled /></form><form id=\"submit\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /><input type=\"submit\" name=\"submit\" value=\"Submit\" /></form><form id=\"select\"><select name=\"fruit\"><option value=\"Apple\">Apple</option><option value=\"Orange\" selected>Orange</option></select></form><form id=\"unnamed\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /><input type=\"text\" value=\"Carrot\" /></form><form id=\"multiple\"><select name=\"fruit\" multiple><option value=\"Apple\" selected>Apple</option><option value=\"Orange\" selected>Orange</option><option value=\"Carrot\">Carrot</option></select></form><form id=\"textarea\"><textarea name=\"fruits\">Apple\nOrange</textarea></form><form id=\"spaces\"><input type=\"text\" name=\"fruit\" value=\"Blood orange\" /></form>",
  "select": "#spaces",
  "op": "serialize"
}
```
Expected output:
```
fruit=Blood+orange
```

#### 6.2 Collect form controls into name/value pairs, skipping disabled and submit controls

Input:
```json
{
  "document": "<form id=\"simple\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /></form><form id=\"nested\"><div><input type=\"text\" name=\"fruit\" value=\"Apple\" /></div><input type=\"text\" name=\"vegetable\" value=\"Carrot\" /></form><form id=\"disabled\"><input type=\"text\" name=\"fruit\" value=\"Apple\" disabled /></form><form id=\"submit\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /><input type=\"submit\" name=\"submit\" value=\"Submit\" /></form><form id=\"select\"><select name=\"fruit\"><option value=\"Apple\">Apple</option><option value=\"Orange\" selected>Orange</option></select></form><form id=\"unnamed\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /><input type=\"text\" value=\"Carrot\" /></form><form id=\"multiple\"><select name=\"fruit\" multiple><option value=\"Apple\" selected>Apple</option><option value=\"Orange\" selected>Orange</option><option value=\"Carrot\">Carrot</option></select></form><form id=\"textarea\"><textarea name=\"fruits\">Apple\nOrange</textarea></form><form id=\"spaces\"><input type=\"text\" name=\"fruit\" value=\"Blood orange\" /></form>",
  "select": "#simple",
  "op": "serialize_array"
}
```
Expected output:
```
fruit=Apple
```

Input:
```json
{
  "document": "<form id=\"simple\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /></form><form id=\"nested\"><div><input type=\"text\" name=\"fruit\" value=\"Apple\" /></div><input type=\"text\" name=\"vegetable\" value=\"Carrot\" /></form><form id=\"disabled\"><input type=\"text\" name=\"fruit\" value=\"Apple\" disabled /></form><form id=\"submit\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /><input type=\"submit\" name=\"submit\" value=\"Submit\" /></form><form id=\"select\"><select name=\"fruit\"><option value=\"Apple\">Apple</option><option value=\"Orange\" selected>Orange</option></select></form><form id=\"unnamed\"><input type=\"text\" name=\"fruit\" value=\"Apple\" /><input type=\"text\" value=\"Carrot\" /></form><form id=\"multiple\"><select name=\"fruit\" multiple><option value=\"Apple\" selected>Apple</option><option value=\"Orange\" selected>Orange</option><option value=\"Carrot\">Carrot</option></select></form><form id=\"textarea\"><textarea name=\"fruits\">Apple\nOrange</textarea></form><form id=\"spaces\"><input type=\"text\" name=\"fruit\" value=\"Blood orange\" /></form>",
  "select": "#submit",
  "op": "serialize_array"
}
```
Expected output:
```
fruit=Apple
```

### Feature 7: Tree traversal

#### 7.1 Walk down the tree with children() and find()

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": "#fruits",
  "op": "children",
  "show": {
    "as": "count"
  }
}
```
Expected output:
```
3
```

Input:
```json
{
  "document": "<ul id=\"food\"><ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul><ul id=\"vegetables\"><li class=\"carrot\">Carrot</li><li class=\"sweetcorn\">Sweetcorn</li></ul></ul>",
  "select": "#food",
  "op": "find",
  "args": {
    "selector": ".apple"
  },
  "show": {
    "as": "text"
  }
}
```
Expected output:
```
Apple
```

#### 7.2 Walk up the tree with parent(), parents() and closest()

Input:
```json
{
  "document": "<ul id=\"food\"><ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul><ul id=\"vegetables\"><li class=\"carrot\">Carrot</li><li class=\"sweetcorn\">Sweetcorn</li></ul></ul>",
  "select": ".apple",
  "op": "parent",
  "show": {
    "as": "attr",
    "name": "id"
  }
}
```
Expected output:
```
error=operation_failed
```

#### 7.3 Navigate sideways with next, prev and siblings

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": ".apple",
  "op": "next",
  "show": {
    "as": "text"
  }
}
```
Expected output:
```
Orange
```

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": ".orange",
  "op": "siblings",
  "show": {
    "as": "count"
  }
}
```
Expected output:
```
2
```

#### 7.4 Reduce a selection with filter, not, eq, first, last and slice

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": "li",
  "op": "filter",
  "args": {
    "selector": ".orange"
  },
  "show": {
    "as": "text"
  }
}
```
Expected output:
```
Orange
```

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": "li",
  "op": "eq",
  "args": {
    "index": 1
  },
  "show": {
    "as": "text"
  }
}
```
Expected output:
```
Orange
```

### Feature 8: DOM manipulation

#### 8.1 Insert content with append, prepend, after and before

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": "#fruits",
  "op": "append",
  "args": {
    "content": "<li class=\"plum\">Plum</li>"
  },
  "show": {
    "select": "#fruits",
    "as": "outer"
  }
}
```
Expected output:
```
<ul id="fruits"><li class="apple">Apple</li><li class="orange">Orange</li><li class="pear">Pear</li><li class="plum">Plum</li></ul>
```

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": ".apple",
  "op": "after",
  "args": {
    "content": "<li class=\"plum\">Plum</li>"
  },
  "show": {
    "select": "#fruits",
    "as": "inner"
  }
}
```
Expected output:
```
<li class="apple">Apple</li><li class="plum">Plum</li><li class="orange">Orange</li><li class="pear">Pear</li>
```

#### 8.2 Wrap and replace nodes

Input:
```json
{
  "document": "<div class=\"inner\">Hello</div>",
  "fragment": true,
  "select": ".inner",
  "op": "wrap",
  "args": {
    "content": "<div class=\"outer\"></div>"
  },
  "show": {
    "select": "@document",
    "as": "outer"
  }
}
```
Expected output:
```
<div class="outer"><div class="inner">Hello</div></div>
```

Input:
```json
{
  "document": "<h2>hi <div>there</div></h2>",
  "fragment": true,
  "select": "div",
  "op": "replace_with",
  "args": {
    "content": "<ul></ul>"
  },
  "show": {
    "select": "h2",
    "as": "outer"
  }
}
```
Expected output:
```
<h2>hi <ul></ul></h2>
```

#### 8.3 Detach nodes with remove and clear children with empty

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": ".pear",
  "op": "remove",
  "show": {
    "select": "#fruits",
    "as": "inner"
  }
}
```
Expected output:
```
<li class="apple">Apple</li><li class="orange">Orange</li>
```

#### 8.4 Read and write inner HTML and text content

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": "#fruits",
  "op": "inner"
}
```
Expected output:
```
<li class="apple">Apple</li><li class="orange">Orange</li><li class="pear">Pear</li>
```

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": "#fruits",
  "op": "text"
}
```
Expected output:
```
AppleOrangePear
```

Input:
```json
{
  "document": "<p>M&amp;M</p>",
  "fragment": true,
  "select": "p",
  "op": "text"
}
```
Expected output:
```
M&M
```

### Feature 9: Serialization and rendering

#### 9.1 Render a selection back to its outer HTML

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": "#fruits",
  "op": "outer"
}
```
Expected output:
```
<ul id="fruits"><li class="apple">Apple</li><li class="orange">Orange</li><li class="pear">Pear</li></ul>
```

#### 9.2 XML mode preserves case and self-closes empty elements

Input:
```json
{
  "document": "<foo></foo>",
  "options": {
    "xml": true
  },
  "select": "foo",
  "op": "outer"
}
```
Expected output:
```
<foo/>
```

Input:
```json
{
  "document": "<MixedCaseTag UPPERCASEATTRIBUTE=\"\"></MixedCaseTag>",
  "options": {
    "xml": true
  },
  "select": "@document",
  "op": "outer"
}
```
Expected output:
```
<MixedCaseTag UPPERCASEATTRIBUTE=""/>
```

### Feature 10: Parsing robustness

#### 10.1 Parser repairs malformed and implicit structures

Input:
```json
{
  "document": "<table><td>bar</td></tr></table>",
  "fragment": true,
  "select": "table tbody tr td",
  "op": "text"
}
```
Expected output:
```
bar
```

Input:
```json
{
  "document": "<xmp><h2></xmp>",
  "fragment": true,
  "select": "xmp",
  "op": "text"
}
```
Expected output:
```
<h2>
```

#### 10.2 Loading a document inserts implicit html/head/body scaffolding

Input:
```json
{
  "document": "<html></html>",
  "select": "@document",
  "op": "outer"
}
```
Expected output:
```
<html><head></head><body></body></html>
```

### Feature 11: Error handling

#### 11.1 Invalid input and invalid selectors map to neutral error categories

Input:
```json
{
  "document": null
}
```
Expected output:
```
error=invalid_input
```

Input:
```json
{
  "document": "<ul id=\"fruits\"><li class=\"apple\">Apple</li><li class=\"orange\">Orange</li><li class=\"pear\">Pear</li></ul>",
  "select": ":bah",
  "op": "count"
}
```
Expected output:
```
error=invalid_selector
```

## Deliverables

- A program that implements the stdin/stdout command protocol described above.
- Correct support for every operation and render kind referenced in the Core
  Features, in both HTML and XML modes.
- Language-neutral error reporting via the `error=<category>` contract.
- The public example cases under `rcb_tests/public_test_cases/` must pass; a
  larger hidden suite under `rcb_tests/test_cases/` exercises the same contracts.
- `bash rcb_tests/test.sh` runs the suite and reports a `test_cases: N/N pass`
  summary.


---
**Implementation notes:**
- handled identically to the standard property getters
- used whenever the inner prompt asks for plain text
