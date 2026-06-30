## Product Requirement Document

# Property-Graph Query Engine over Relational Tables (SQL/PGQ) - Pattern Matching, Paths & Schema Introspection

## Project Goal

Build a query engine that lets developers define a *property graph* as a logical view over ordinary relational tables and then run graph pattern-matching queries against it, so they can express reachability, neighborhood and path questions declaratively instead of hand-writing recursive joins. The engine extends a SQL database with the SQL/PGQ surface: a statement to declare a graph from existing tables, a table-valued `GRAPH_TABLE ( ... MATCH ... COLUMNS ... )` operator that turns graph patterns into relational rows, descriptor functions for paths, and introspection functions for the declared schema.

---

## Background & Problem

A property graph is a set of **vertices** and **edges** drawn from existing tables. A vertex table contributes one vertex per row; an edge table contributes one edge per row, where two foreign-key-style columns (a SOURCE KEY and a DESTINATION KEY) reference the key columns of the source and destination vertex tables. Vertices and edges carry a **label** (a logical type name) and a set of **properties** (the columns exposed for matching and projection).

Without such an engine, developers express graph questions as verbose, error-prone self-joins and recursive CTEs, re-deriving adjacency by hand for every query and every fan-out depth. This engine provides one declarative contract: declare the graph once, then match patterns like `(a:Person)-[k:Knows]->(b:Person)` and project columns out of the matched bindings, including variable-length and shortest-path patterns.

**Worked example graph used throughout.** Most features below are illustrated with the same small graph: a `Student(id, name)` vertex table labelled `Person`, a `know(src, dst, createDate)` edge table labelled `Knows` (source and destination both reference `Student(id)`), a `School(name, Id, Kind)` vertex table labelled `SCHOOL`, and a `StudyAt(personId, schoolId)` edge table labelled `StudyAt` (from `Student(id)` to `School(id)`). The five students are Daniel(0), Tavneet(1), Gabor(2), Peter(3), David(4); the `know` edges are 0->1, 0->2, 0->3, 3->0, 1->2, 1->3, 2->3, 4->3.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility system (graph-definition catalog, pattern compiler/binder, match execution, path search, output and error rendering); it MUST NOT be a single "god file". Output a clear, multi-file directory tree that reflects a production-grade repository. Do not over-engineer, but strictly avoid monolithic files.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases represent a **black-box testing contract** for the execution adapter, NOT the internal data model. The core engine must be decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating a JSON command into engine calls and rendering results.

3. **Adherence to SOLID Design Principles:** Separate parsing, binding/validation, match execution, path search, and output formatting into distinct logical units (SRP); keep the engine open for extension but closed for modification (OCP); model labels/subtypes substitutably (LSP); keep interfaces small (ISP); depend on abstractions, not on I/O details (DIP).

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic. The system must handle edge cases gracefully and model errors as categorized, domain-level failures (invalid definition, parser, binder, constraint, catalog, not-implemented) rather than generic faults.

---

## Core Features

### Feature 1: Property-Graph Definition, Introspection & Lifecycle

**As a developer**, I want to declare a graph from existing tables, inspect it, and drop it, so I can manage graph definitions as first-class catalog objects.

**Expected Behavior / Usage:**

A definition lists VERTEX TABLES and optional EDGE TABLES. Each vertex/edge table names a backing base table (optionally aliased), an optional property list (`PROPERTIES ( ... )`, or all columns by default, or `PROPERTIES ALL COLUMNS EXCEPT ( ... )`), and a `LABEL`. A label may declare subtypes via a discriminator: `LABEL Base IN <discriminator> ( sub1, sub2 )`. Edge tables additionally declare `SOURCE KEY ( ... ) REFERENCES <vtable> ( ... )` and `DESTINATION KEY ( ... ) REFERENCES <vtable> ( ... )`.

*1.1 Describe a defined graph — one descriptor row per element table*

Describing a graph returns one row per element table with: backing table name, the normalized (lower-cased) label, a boolean that is [boolean literal for vertex flag] for vertices and false for edges, and — for edges only — the source vertex table, source key column list, source-referenced key list, destination vertex table, destination key column list, destination-referenced key list. Vertex rows leave the edge-specific fields empty (rendered as `[boolean literal for vertex flag]`). A label declared with a subtype discriminator additionally reports the discriminator name and the bracketed, ordered list of sublabels in the last two fields. Column-list fields render as a bracketed list such as `[id]`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_describe_graph.json`

```json
{
    "description": "Define a property graph over existing base tables and ask the engine to describe it. The description is one row per element table: the backing table name, the normalized (lower-cased) label, a flag indicating whether the element is a vertex, and for edges the source/destination vertex table with their key column lists. Vertex rows leave the edge-specific fields empty, and a label declared with a subtype discriminator additionally reports the discriminator name and the ordered list of sublabels.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, createDate BIGINT)",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17)",
                    "CREATE TABLE School(name VARCHAR, Id BIGINT, Kind VARCHAR)",
                    "INSERT INTO School VALUES ('VU',0,'University'),('UVA',1,'University')",
                    "CREATE TABLE StudyAt(personId BIGINT, schoolId BIGINT)",
                    "INSERT INTO StudyAt VALUES (0,0),(1,0),(2,1),(3,1),(4,1)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person, School LABEL SCHOOL) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (createDate) LABEL Knows, studyAt SOURCE KEY (personId) REFERENCES Student (id) DESTINATION KEY (SchoolId) REFERENCES School (id) LABEL StudyAt)"
                ],
                "query": "DESCRIBE PROPERTY GRAPH pg"
            },
            "expected_output": "School\tschool\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\nStudent\tperson\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\nstudyAt\tstudyat\tfalse\tStudent\t[id]\t[personId]\tSchool\t[id]\t[SchoolId]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\nknow\tknows\tfalse\tStudent\t[id]\t[src]\tStudent\t[id]\t[dst]\t[boolean literal for vertex flag]\t[boolean literal for vertex flag]\n"
        }
    ]
}
```

*1.2 Reject invalid definitions — categorized error*

A definition that names a non-existent base table (as a vertex or as an edge), that has an edge whose key references a vertex table not listed in the definition, that repeats the same label within one definition, or that is syntactically illegal (for example a wildcard property list) is rejected. Each failure is rendered as a neutral two-line block: `error=<category>` then `message=<engine message>`. Categories observed here include `invalid`, `parser` and `constraint`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_definition_errors.json`

```json
{
    "description": "Reject an invalid property-graph definition with a categorized error. A vertex or edge table that names a non-existent base table is rejected; an edge whose key references a vertex table not listed in the definition is rejected; repeating the same label within one definition is rejected; and syntactically illegal definition text (such as a wildcard property list) is rejected at parse time. Each failure is reported as a neutral category plus the engine's explanatory message.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter')",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, createDate BIGINT)",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(1,2,14),(1,3,15),(2,3,16)",
                    "CREATE TABLE School(school_name VARCHAR, school_id BIGINT, school_kind BIGINT)",
                    "INSERT INTO School VALUES ('VU',0,0),('UVA',1,1)"
                ],
                "query": "CREATE PROPERTY GRAPH pgx VERTEX TABLES (tabledoesnotexist)"
            },
            "expected_output": "error=invalid\nmessage=tabledoesnotexist does not exist\n"
        }
    ]
}
```

*1.3 Drop a graph and observe it is gone*

After a graph is dropped, matching against it fails, dropping it again fails, and dropping a graph that never existed fails. Each failure is the neutral `error=binder` / `message=...` block, where the message names the missing graph.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_drop_graph.json`

```json
{
    "description": "Remove a property graph and observe that it is gone. After a graph is dropped, matching against it fails, dropping it a second time fails, and dropping a graph that never existed fails. Each failure is reported as a neutral category plus the engine message naming the missing graph.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, createDate BIGINT)",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17)",
                    "CREATE TABLE School(name VARCHAR, Id BIGINT, Kind VARCHAR)",
                    "INSERT INTO School VALUES ('VU',0,'University'),('UVA',1,'University')",
                    "CREATE TABLE StudyAt(personId BIGINT, schoolId BIGINT)",
                    "INSERT INTO StudyAt VALUES (0,0),(1,0),(2,1),(3,1),(4,1)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person, School LABEL SCHOOL) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (createDate) LABEL Knows, studyAt SOURCE KEY (personId) REFERENCES Student (id) DESTINATION KEY (SchoolId) REFERENCES School (id) LABEL StudyAt)",
                    "DROP PROPERTY GRAPH pg"
                ],
                "query": "SELECT study.id FROM GRAPH_TABLE (pg MATCH (a:Person) COLUMNS (a.id)) study"
            },
            "expected_output": "error=binder\nmessage=Property graph pg does not exist\n"
        }
    ]
}
```

---

### Feature 2: Vertex Pattern Matching & Projection

**As a developer**, I want to match vertices by label, filter them, and project their properties, so I can read graph data with familiar SQL semantics.

**Expected Behavior / Usage:**

A `GRAPH_TABLE` invocation names the graph, a `MATCH` pattern, and a `COLUMNS ( ... )` projection list; the operator yields a relational table that can be aliased and used like any subquery. Each projected expression may be aliased; the surrounding SELECT references those projected columns through the subquery alias.

*2.1 Project specific properties, optionally filtered*

A single-vertex pattern `(a:Label)` matches every vertex with that label. An optional `WHERE` predicate over a vertex property restricts the matches. The output has one row per matched vertex, columns following the COLUMNS list in order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_vertex_projection.json`

```json
{
    "description": "Match every vertex carrying a given label and project chosen properties. A WHERE predicate on a vertex property restricts the matched vertices; the projected columns follow the COLUMNS list in order. Output is one row per matched vertex.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, createDate BIGINT)",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17)",
                    "CREATE TABLE School(name VARCHAR, Id BIGINT, Kind VARCHAR)",
                    "INSERT INTO School VALUES ('VU',0,'University'),('UVA',1,'University')",
                    "CREATE TABLE StudyAt(personId BIGINT, schoolId BIGINT)",
                    "INSERT INTO StudyAt VALUES (0,0),(1,0),(2,1),(3,1),(4,1)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person, School LABEL SCHOOL) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (createDate) LABEL Knows, studyAt SOURCE KEY (personId) REFERENCES Student (id) DESTINATION KEY (SchoolId) REFERENCES School (id) LABEL StudyAt)"
                ],
                "query": "SELECT study.a_id, study.name FROM GRAPH_TABLE (pg MATCH (a:Person) WHERE a.id = 0 COLUMNS (a.id as a_id, a.name)) study"
            },
            "expected_output": "0\tDaniel\n"
        }
    ]
}
```

*2.2 Wildcard projection of a vertex's properties*

A wildcard projection `(<var>.*)` expands, in declaration order, to every property exposed for that vertex's label. Over an edge pattern, the bound endpoint's properties are emitted once per matched edge (so a vertex with three outgoing edges appears three times).

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_vertex_wildcard.json`

```json
{
    "description": "Project all properties of a bound vertex with a wildcard projection. The wildcard expands, in declaration order, to every property exposed for that vertex's label. Used over an edge pattern, the bound endpoint's properties are emitted once per matched edge.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, createDate BIGINT)",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17)",
                    "CREATE TABLE School(name VARCHAR, Id BIGINT, Kind VARCHAR)",
                    "INSERT INTO School VALUES ('VU',0,'University'),('UVA',1,'University')",
                    "CREATE TABLE StudyAt(personId BIGINT, schoolId BIGINT)",
                    "INSERT INTO StudyAt VALUES (0,0),(1,0),(2,1),(3,1),(4,1)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person, School LABEL SCHOOL) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (createDate) LABEL Knows, studyAt SOURCE KEY (personId) REFERENCES Student (id) DESTINATION KEY (SchoolId) REFERENCES School (id) LABEL StudyAt)"
                ],
                "query": "FROM GRAPH_TABLE (pg MATCH (a:Person) COLUMNS (a.*)) study ORDER BY study.id, study.name"
            },
            "expected_output": "0\tDaniel\n1\tTavneet\n2\tGabor\n3\tPeter\n4\tDavid\n"
        }
    ]
}
```

*2.3 Aggregation over matches*

An aggregate expression inside the COLUMNS list collapses all matches to a single value (e.g. an average). An outer GROUP BY over a projected column, with ORDER BY, produces grouped counts.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_vertex_aggregation.json`

```json
{
    "description": "Apply aggregation to the rows produced by a graph pattern. An aggregate inside the COLUMNS list collapses the matches to a single value, and an outer GROUP BY over a projected column with ORDER BY produces grouped counts.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, createDate BIGINT)",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17)",
                    "CREATE TABLE School(name VARCHAR, Id BIGINT, Kind VARCHAR)",
                    "INSERT INTO School VALUES ('VU',0,'University'),('UVA',1,'University')",
                    "CREATE TABLE StudyAt(personId BIGINT, schoolId BIGINT)",
                    "INSERT INTO StudyAt VALUES (0,0),(1,0),(2,1),(3,1),(4,1)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person, School LABEL SCHOOL) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (createDate) LABEL Knows, studyAt SOURCE KEY (personId) REFERENCES Student (id) DESTINATION KEY (SchoolId) REFERENCES School (id) LABEL StudyAt)"
                ],
                "query": "SELECT * FROM GRAPH_TABLE (pg MATCH (a:Person)-[k:Knows]->(b:Person) COLUMNS (avg(a.id))) study"
            },
            "expected_output": "1.375\n"
        }
    ]
}
```

---

### Feature 3: Edge Pattern Matching

**As a developer**, I want to match edges between labelled vertices with direction, chain multiple edges, and rely on case-insensitive label names, so I can express neighborhood and multi-hop queries.

**Expected Behavior / Usage:**

*3.1 Directional edge matching*

A right arrow `-[:Label]->` matches edges leaving the first vertex; a left arrow `<-[:Label]-` matches edges entering it; an undirected edge `-[:Label]-` matches in either orientation (so a reciprocal pair between two vertices yields two matches); a both-directions edge `<-[:Label]->` matches only when edges exist in both orientations between the same pair.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_edge_direction.json`

```json
{
    "description": "Match a single edge between two labelled vertices, honoring the direction written in the pattern. A right arrow matches edges leaving the first vertex; a left arrow matches edges entering it; an undirected edge matches in either orientation (so a reciprocal pair yields two matches); and a both-directions edge matches only when edges exist in both orientations between the same pair.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, createDate BIGINT)",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17)",
                    "CREATE TABLE School(name VARCHAR, Id BIGINT, Kind VARCHAR)",
                    "INSERT INTO School VALUES ('VU',0,'University'),('UVA',1,'University')",
                    "CREATE TABLE StudyAt(personId BIGINT, schoolId BIGINT)",
                    "INSERT INTO StudyAt VALUES (0,0),(1,0),(2,1),(3,1),(4,1)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person, School LABEL SCHOOL) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (createDate) LABEL Knows, studyAt SOURCE KEY (personId) REFERENCES Student (id) DESTINATION KEY (SchoolId) REFERENCES School (id) LABEL StudyAt)"
                ],
                "query": "SELECT study.a_name, study.b_name FROM GRAPH_TABLE (pg MATCH (a:Person)-[k:Knows]->(b:Person) WHERE a.name = 'Daniel' COLUMNS (a.name as a_name, b.name as b_name)) study ORDER BY a_name, b_name"
            },
            "expected_output": "Daniel\tGabor\nDaniel\tPeter\nDaniel\tTavneet\n"
        }
    ]
}
```

*3.2 Multi-hop and join patterns*

Patterns may chain several edges, re-enter the starting vertex (e.g. a triangle `(a)->(b)->(c)->(a)`), and join two different edge types through a shared middle vertex. Projected columns may come from any vertex bound in the pattern.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_multi_hop.json`

```json
{
    "description": "Match patterns that chain several edges, including patterns that re-enter the starting vertex and patterns that join two different edge types through a shared middle vertex. The projected columns may come from any vertex bound in the pattern.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, createDate BIGINT)",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17)",
                    "CREATE TABLE School(name VARCHAR, Id BIGINT, Kind VARCHAR)",
                    "INSERT INTO School VALUES ('VU',0,'University'),('UVA',1,'University')",
                    "CREATE TABLE StudyAt(personId BIGINT, schoolId BIGINT)",
                    "INSERT INTO StudyAt VALUES (0,0),(1,0),(2,1),(3,1),(4,1)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person, School LABEL SCHOOL) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (createDate) LABEL Knows, studyAt SOURCE KEY (personId) REFERENCES Student (id) DESTINATION KEY (SchoolId) REFERENCES School (id) LABEL StudyAt)"
                ],
                "query": "SELECT study.a_name, study.b_name, study.c_name FROM GRAPH_TABLE (pg MATCH (a:Person)-[k:Knows]->(b:Person)-[k2:Knows]->(c:Person)-[k3:Knows]->(a:Person) COLUMNS (a.name as a_name, b.name as b_name, c.name as c_name)) study ORDER BY study.a_name, study.b_name, study.c_name"
            },
            "expected_output": "Daniel\tGabor\tPeter\nDaniel\tTavneet\tPeter\nGabor\tPeter\tDaniel\nPeter\tDaniel\tGabor\nPeter\tDaniel\tTavneet\nTavneet\tPeter\tDaniel\n"
        }
    ]
}
```

*3.3 Case-insensitive labels*

Label references in a pattern match case-insensitively, producing the same result set regardless of how vertex and edge labels are capitalized.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_case_insensitive_labels.json`

```json
{
    "description": "Label references in a pattern are matched case-insensitively, so the same result set is produced regardless of how vertex and edge labels are capitalized in the query.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, createDate BIGINT)",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17)",
                    "CREATE TABLE School(name VARCHAR, Id BIGINT, Kind VARCHAR)",
                    "INSERT INTO School VALUES ('VU',0,'University'),('UVA',1,'University')",
                    "CREATE TABLE StudyAt(personId BIGINT, schoolId BIGINT)",
                    "INSERT INTO StudyAt VALUES (0,0),(1,0),(2,1),(3,1),(4,1)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person, School LABEL SCHOOL) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (createDate) LABEL Knows, studyAt SOURCE KEY (personId) REFERENCES Student (id) DESTINATION KEY (SchoolId) REFERENCES School (id) LABEL StudyAt)"
                ],
                "query": "SELECT * FROM GRAPH_TABLE (pg MATCH (a:Person)-[k:Knows]->(b:Person) COLUMNS (a.name as a_name, b.name as b_name)) study ORDER BY a_name, b_name"
            },
            "expected_output": "Daniel\tGabor\nDaniel\tPeter\nDaniel\tTavneet\nDavid\tPeter\nGabor\tPeter\nPeter\tDaniel\nTavneet\tGabor\nTavneet\tPeter\n"
        }
    ]
}
```

---

### Feature 4: Label Inheritance (Subtypes)

**As a developer**, I want a vertex table to carry a base label plus subtype labels selected by a discriminator column, so I can query the whole population or a specific subtype with one definition.

**Expected Behavior / Usage:**

A vertex table may declare `LABEL Base IN <discriminator> ( subA, subB )`. Matching the base label returns every row of the table. Matching a subtype label returns only the rows whose discriminator column selects that subtype (the first declared subtype maps to discriminator value 1, the second to 2, and so on). Subtype matching is case-insensitive.

**Test Cases:** `rcb_tests/public_test_cases/feature4_label_inheritance.json`

```json
{
    "description": "A vertex table may declare a base label together with subtype labels keyed off a discriminator column. Matching the base label returns every row of the table, while matching a subtype label returns only the rows whose discriminator selects that subtype. Subtype matching is case-insensitive.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Person(id BIGINT, name VARCHAR)",
                    "CREATE TABLE Organisation(name VARCHAR, id BIGINT, mask BIGINT)",
                    "CREATE TABLE Company(name VARCHAR, id BIGINT, mask VARCHAR)",
                    "CREATE TABLE University(name VARCHAR, id BIGINT, mask VARCHAR)",
                    "CREATE TABLE worksAt(personId BIGINT, organisationId BIGINT)",
                    "INSERT INTO Person VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "INSERT INTO worksAt VALUES (0,1),(0,2),(0,3),(1,2),(1,3),(2,3),(3,0),(4,3)",
                    "INSERT INTO University VALUES ('VU',0,1),('UvA',1,1)",
                    "INSERT INTO Company VALUES ('EY',2,2),('CWI',3,2)",
                    "INSERT INTO Organisation (SELECT * from university union select * from company)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Person LABEL Person, Organisation LABEL Organisation IN mask(university, company)) EDGE TABLES (worksAt SOURCE KEY (personId) REFERENCES Person (id) DESTINATION KEY (organisationId) REFERENCES Organisation (id) LABEL worksAt)"
                ],
                "query": "SELECT * FROM GRAPH_TABLE (pg MATCH (p:Person)-[w:worksAt]->(u:organisation) COLUMNS (p.id as p_id, p.name as p_name, u.id as u_id, u.name as u_name)) result ORDER BY p_id, u_id"
            },
            "expected_output": "0\tDaniel\t1\tUvA\n0\tDaniel\t2\tEY\n0\tDaniel\t3\tCWI\n1\tTavneet\t2\tEY\n1\tTavneet\t3\tCWI\n2\tGabor\t3\tCWI\n3\tPeter\t0\tVU\n4\tDavid\t3\tCWI\n"
        }
    ]
}
```

---

### Feature 5: Variable-Length & Shortest Paths

**As a developer**, I want to match paths whose hop count varies within a bound, ask for the shortest such path, and read path descriptors, so I can answer reachability questions.

**Expected Behavior / Usage:**

*5.1 Bounded repetition, shortest paths and path descriptors*

A quantifier `->{m,n}` on an edge matches paths of between `m` and `n` hops. Prefixing the pattern with `<var> = ANY SHORTEST` binds a path variable and returns, for each reachable endpoint, one shortest qualifying path. Descriptor functions over the path variable expose its element-id sequence (`element_id(p)`, rendered as a bracketed list of vertex/edge dense ids alternating along the path) and its hop count (`path_length(p)`). A bounded repetition without the shortest qualifier returns each endpoint reachable within the bound.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_variable_length_paths.json`

```json
{
    "description": "Match paths whose hop count varies within a bounded range. A shortest-path pattern returns, for each reachable endpoint, the shortest qualifying path; path descriptor functions expose the path's element-id sequence and its length (number of edges). A bounded repetition without the shortest qualifier returns each endpoint reachable within the bound.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, createDate BIGINT)",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17)",
                    "CREATE TABLE School(name VARCHAR, Id BIGINT, Kind VARCHAR)",
                    "INSERT INTO School VALUES ('VU',0,'University'),('UVA',1,'University')",
                    "CREATE TABLE StudyAt(personId BIGINT, schoolId BIGINT)",
                    "INSERT INTO StudyAt VALUES (0,0),(1,0),(2,1),(3,1),(4,1)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person, School LABEL SCHOOL) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (createDate) LABEL Knows, studyAt SOURCE KEY (personId) REFERENCES Student (id) DESTINATION KEY (SchoolId) REFERENCES School (id) LABEL StudyAt)"
                ],
                "query": "FROM GRAPH_TABLE (pg MATCH p = ANY SHORTEST (a:Person WHERE a.name = 'Daniel')-[k:knows]->{1,3}(b:Person) COLUMNS (element_id(p), a.name as name, b.name as b_name)) study ORDER BY b_name"
            },
            "expected_output": "[0, 1, 2]\tDaniel\tGabor\n[0, 2, 3]\tDaniel\tPeter\n[0, 0, 1]\tDaniel\tTavneet\n"
        }
    ]
}
```

*5.2 Reject unsupported or unsafe path patterns*

An unbounded quantifier (`*` or `+`) under the default walk semantics is rejected because it could produce infinite results (`[path query with infinite results]`). Path modes other than walk (e.g. TRAIL, ACYCLIC, SIMPLE) and the `ALL SHORTEST` qualifier are rejected as not implemented (`error=not_implemented`). Projecting a bare path variable that was not exposed as a descriptor column is rejected by the binder (`error=binder`).

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_path_errors.json`

```json
{
    "description": "Reject path patterns that are unsupported or unsafe. An unbounded quantifier under the default walk semantics is rejected because it could produce infinite results; path modes other than walk and the all-shortest qualifier are rejected as not implemented; and projecting a bare path variable that is not exposed as a column is rejected by the binder. Each failure is a neutral category plus the engine message.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, createDate BIGINT)",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17)",
                    "CREATE TABLE School(name VARCHAR, Id BIGINT, Kind VARCHAR)",
                    "INSERT INTO School VALUES ('VU',0,'University'),('UVA',1,'University')",
                    "CREATE TABLE StudyAt(personId BIGINT, schoolId BIGINT)",
                    "INSERT INTO StudyAt VALUES (0,0),(1,0),(2,1),(3,1),(4,1)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person, School LABEL SCHOOL) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (createDate) LABEL Knows, studyAt SOURCE KEY (personId) REFERENCES Student (id) DESTINATION KEY (SchoolId) REFERENCES School (id) LABEL StudyAt)"
                ],
                "query": "SELECT study.a_name, study.b_name FROM GRAPH_TABLE (pg MATCH (a:Person WHERE a.name = 'Peter')-[k:Knows]-> *(b:Person) COLUMNS (a.name as a_name, b.name as b_name)) study"
            },
            "expected_output": "[path query with infinite results]\nmessage=ALL unbounded with path mode WALK is not possible as this could lead to infinite results. Consider specifying an upper bound or path mode other than WALK\n"
        }
    ]
}
```

---

### Feature 6: Graph Schema & Adjacency Introspection Functions

**As a developer**, I want table-valued functions that report a graph's schema and its compiled adjacency structure, so I can inspect and reuse the graph programmatically.

**Expected Behavior / Usage:**

*6.1 Schema name functions*

Given a graph name, `get_pg_vtablenames(<graph>)` returns its vertex table names, `get_pg_etablenames(<graph>)` returns its edge table names, and `get_pg_vcolnames(<graph>, <table>)` / `get_pg_ecolnames(<graph>, <table>)` return the property column names of a named vertex/edge table. Each returns one row per name.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_schema_functions.json`

```json
{
    "description": "Table-valued functions expose a defined graph's schema: the set of vertex table names, the set of edge table names, and the property column names for a named vertex or edge table. Each returns one row per name.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, id BIGINT)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17),(2,4,18)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (id) LABEL Knows)"
                ],
                "query": "SELECT * from get_pg_vtablenames('pg')"
            },
            "expected_output": "Student\n"
        }
    ]
}
```

*6.2 Compiled adjacency (CSR) functions*

After a compressed sparse-row adjacency structure is built from the edge list (keyed by a small integer id), `get_csr_v(<id>)` returns the per-vertex offset array — a prefix-sum of out-degrees with one entry per vertex plus a terminating total — and `get_csr_e(<id>)` returns the flattened destination array of neighbor dense ids in adjacency order. Each returns one value per row.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_csr_functions.json`

```json
{
    "description": "After building a compressed sparse-row adjacency structure from the edge list, two functions read it back: one returns the per-vertex offset array (a prefix-sum of out-degrees, one entry per vertex plus a terminating total) and the other returns the flattened destination array of neighbor dense ids in adjacency order.",
    "cases": [
        {
            "input": {
                "setup": [
                    "CREATE TABLE Student(id BIGINT, name VARCHAR)",
                    "CREATE TABLE know(src BIGINT, dst BIGINT, id BIGINT)",
                    "INSERT INTO Student VALUES (0,'Daniel'),(1,'Tavneet'),(2,'Gabor'),(3,'Peter'),(4,'David')",
                    "INSERT INTO know VALUES (0,1,10),(0,2,11),(0,3,12),(3,0,13),(1,2,14),(1,3,15),(2,3,16),(4,3,17),(2,4,18)",
                    "CREATE PROPERTY GRAPH pg VERTEX TABLES (Student PROPERTIES (id,name) LABEL Person) EDGE TABLES (know SOURCE KEY (src) REFERENCES Student (id) DESTINATION KEY (dst) REFERENCES Student (id) PROPERTIES (id) LABEL Knows)",
                    "SELECT CREATE_CSR_EDGE(0,(SELECT count(a.id) FROM Student a),CAST((SELECT sum(CREATE_CSR_VERTEX(0,(SELECT count(a.id) FROM Student a),sub.dense_id,sub.cnt)) FROM (SELECT a.rowid as dense_id, count(k.src) as cnt FROM Student a LEFT JOIN Know k ON k.src = a.id GROUP BY a.rowid) sub) AS BIGINT),a.rowid,c.rowid,k.rowid) as temp FROM Know k JOIN student a on a.id = k.src JOIN student c on c.id = k.dst"
                ],
                "query": "SELECT * from get_csr_v(0)"
            },
            "expected_output": "0\n3\n5\n7\n8\n9\n9\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above: a catalog of property-graph definitions built over base tables, a binder that validates patterns and labels, a match executor for fixed and variable-length patterns, a shortest-path search, and schema/adjacency introspection. The core must be decoupled from stdin/stdout and JSON parsing.

2. **The Execution/Test Adapter:** A runnable entry point, logically separated from the core, that reads a single JSON request from stdin and writes the result of one observed statement to stdout. The request has an optional `setup` array of SQL statements (table creation, data loading, graph definition) that are executed silently to establish state, and a `query` string — the one statement whose result is rendered. Rendering contract:
   - A statement that returns rows renders one line per row, columns separated by a TAB (`\t`), with `[boolean literal for vertex flag]` shown as the literal text `[boolean literal for vertex flag]` and list/array values shown as `[a, b, c]`. A trailing newline follows every row. Row order is whatever the statement specifies via `ORDER BY` (deterministic single-threaded execution otherwise).
   - A statement that fails renders a language-neutral two-line block: `error=<category>` then `message=<engine message>`, each followed by a newline. `<category>` is the snake_case engine error class (`invalid`, `parser`, `binder`, `constraint`, `catalog`, `not_implemented`). Host-runtime decorations (source-line echoes, caret markers, "Did you mean ..." hints) are stripped.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`, namespaced by `<cases-dir>`. Each `.txt` contains **only** the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- nulls for dest_table++
- eün-direction pattern
