## Product Requirement Document

# Admin Panel Access-Control Permission Toolkit - Permission-name generation, component discovery, and role synchronization

## Project Goal

Build a permission-management toolkit for an admin-panel framework that automatically derives stable permission identifiers for every administrative component (data resources, standalone pages, dashboard widgets), discovers the components an application exposes, and synchronizes the generated permissions onto a privileged "super-admin" role. The toolkit lets developers wire role-based access control into an admin panel without hand-writing and hand-maintaining permission strings for each screen and action.

---

## Background & Problem

Without this toolkit, developers must manually invent and maintain a permission string for every action on every administrative screen — typically a dozen action variants per data resource plus one per page and per widget — and must remember to grant each new permission to privileged roles. This is repetitive, drift-prone boilerplate: a renamed screen or a forgotten action silently leaves a hole in the authorization model, and the naming scheme tends to diverge across a team.

With this toolkit, permission identifiers are derived deterministically from the component classes themselves, the full set of components is discovered automatically (with an opt-out exclusion list), and every generated permission is synchronized onto the super-admin role in one pass — so access control stays complete and consistent as the panel grows.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This domain has several distinct responsibilities (identifier derivation, component discovery, permission generation, role synchronization, prefix resolution). It MUST NOT be a single "god file"; output a clear multi-file tree (core domain modules plus an execution adapter) that reflects a production-grade repository. Do not over-engineer, but strictly avoid a monolith.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. Core logic must remain decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain and for rendering the normalized output.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units (SRP). The core engine must be open for extension (e.g., pluggable naming strategies and per-component prefix sets) but closed for modification (OCP). Keep interfaces small and cohesive (ISP); depend on abstractions, not on I/O details (DIP).

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic, hiding internal complexity. Edge cases (excluded components, idempotent re-registration, invalid identifiers) must be handled explicitly. Errors must be modeled as proper error types rather than generic faults; the adapter renders them as neutral, language-independent error contracts.

---

## Core Features

### Feature 1: Permission Identifier Derivation

**As a developer**, I want each administrative data-resource class to map to a single stable, human-readable permission identifier, so I can build every action permission for that resource on a predictable naming base.

**Expected Behavior / Usage:**

An administrative data resource is identified by its fully-qualified class name (conventionally namespaced under a `...\Resources\` segment and named with a trailing `Resource` suffix) plus the fully-qualified class name of the model it manages. From a resource class the toolkit derives one canonical permission identifier. Word boundaries in the identifier are joined by a double-colon (`::`) separator, never by an underscore — underscores are reserved as the delimiter between an action prefix and the resource identifier inside generated permission names, so any identifier that would contain an underscore is invalid.

*1.1 Default identifier strategy — derive the identifier from the resource class name*

The default strategy takes the resource class name, removes everything up to and including the conventional resources-namespace segment, drops the trailing role/`Resource` suffix, and converts the remaining words to a lowercase token in which boundaries between words become a double-colon. A single-word resource name yields a single lowercase token with no separator; a multi-word resource name yields tokens joined by `::`. The adapter emits one line per input resource, in the order supplied, pairing the resource class with its derived identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_default_identifier.json`

```json
{
    "description": "Derive the canonical permission identifier for one or more administrative resource classes using the default naming strategy. Each resource is identified by its fully-qualified class name and its backing model class. The default strategy takes the resource class name, strips a trailing role-segment suffix, and converts the remaining words into a lowercase token where word boundaries are joined by a double-colon separator. The adapter emits one line per resource pairing the input class with its derived identifier, in the order supplied.",
    "cases": [
        {
            "input": {"op": "permission_identifier", "resources": [{"fqcn": "App\\Filament\\Resources\\BlogPostResource", "model": "App\\Models\\BlogPost"}, {"fqcn": "App\\Filament\\Resources\\OrderResource", "model": "App\\Models\\Order"}]},
            "expected_output": "class=App\\Filament\\Resources\\BlogPostResource identifier=blog::post\nclass=App\\Filament\\Resources\\OrderResource identifier=order\n"
        }
    ]
}
```

*1.2 Configured identifier strategy — derive the identifier from the backing model*

The derivation strategy is pluggable. With the "model basename, lowercased" strategy, the identifier is computed from the resource's backing model class: take the final segment of the model class name and lowercase it. The adapter emits one line pairing the resource class with the derived identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_closure_identifier.json`

```json
{
    "description": "Derive a resource's permission identifier using a configured naming strategy instead of the default. The strategy 'model basename lower' computes the identifier from the resource's backing model: it takes the final segment of the model class name and lowercases it. The adapter emits one line pairing the resource class with the derived identifier.",
    "cases": [
        {
            "input": {"op": "permission_identifier", "strategy": {"type": "model_basename_lower"}, "resources": [{"fqcn": "App\\Filament\\Resources\\BlogPostResource", "model": "App\\Models\\BlogPost"}]},
            "expected_output": "class=App\\Filament\\Resources\\BlogPostResource identifier=blogpost\n"
        }
    ]
}
```

*1.3 Invalid identifier rejection — reject identifiers containing an underscore*

Because underscore is reserved as the prefix/identifier delimiter, a configured strategy that produces an underscore-containing token is invalid. With the "model basename, snake-cased" strategy applied to a multi-word model name (which introduces an underscore), the derivation is rejected. The adapter emits a neutral error line carrying the offending resource class and the rejected identifier rather than returning a value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_identifier_underscore_rejected.json`

```json
{
    "description": "Reject a configured naming strategy that produces an identifier containing an underscore. A permission identifier must not contain underscore characters, because underscores are reserved as the delimiter between an action prefix and a resource identifier in generated permission names. When the configured strategy yields an underscore-containing token (here, converting the model basename to snake_case for a multi-word model name), the operation is rejected and the adapter emits a neutral error line carrying the offending resource class and the rejected identifier.",
    "cases": [
        {
            "input": {"op": "permission_identifier", "strategy": {"type": "model_basename_snake"}, "resources": [{"fqcn": "App\\Filament\\Resources\\BlogPostResource", "model": "App\\Models\\BlogPost"}]},
            "expected_output": "error=identifier_has_underscore class=App\\Filament\\Resources\\BlogPostResource identifier=blog_post\n"
        }
    ]
}
```

---

### Feature 2: Component Discovery

**As a developer**, I want the toolkit to enumerate every administrative component my application exposes and project each into its permission key, so I never hand-maintain the list of screens that need permissions.

**Expected Behavior / Usage:**

The toolkit enumerates three kinds of registered components — data resources, standalone pages, and dashboard widgets — and projects each into the permission space. Discovery honors an opt-out exclusion list: when exclusion is enabled, any component whose short (unqualified) class name appears in the configured exclusion list is omitted. Page and widget permission names are built by joining a configured action prefix and the component's short class name with an underscore.

*2.1 Resource discovery — registered resources to a sorted identifier/model map*

For each registered data resource the toolkit derives its permission identifier (per Feature 1's default strategy) and attaches the short name of the resource's model. The result is sorted by identifier. A built-in role-management resource is always present in the result in addition to the application's own resources. The adapter emits one line per discovered resource, sorted by identifier, carrying the identifier and the model short name.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_discover_resources.json`

```json
{
    "description": "Discover the set of administrative resources visible to the permission system and project them into a sorted permission map. Given a set of registered resource classes (each with its backing model), the system derives each resource's permission identifier, attaches the model's short name, and returns the entries sorted by identifier. A built-in role-management resource is always present in the set in addition to the supplied resources. The adapter emits one line per discovered resource, sorted by identifier, carrying the identifier and the model short name.",
    "cases": [
        {
            "input": {"op": "discover_resources", "resources": [{"fqcn": "App\\Filament\\Resources\\PostResource", "model": "App\\Models\\Post"}, {"fqcn": "App\\Filament\\Resources\\BlogCategoryResource", "model": "App\\Models\\BlogCategory"}]},
            "expected_output": "resource=blog::category model=BlogCategory\nresource=post model=Post\nresource=role model=Role\n"
        }
    ]
}
```

*2.2 Resource discovery with exclusion — drop resources by short class name*

When exclusion is enabled and a registered resource's short class name appears in the exclusion list, that resource is dropped from the result. The built-in role-management resource remains present. The adapter emits one line per surviving resource, sorted by identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_discover_resources_excluded.json`

```json
{
    "description": "Discover resources while applying an exclusion list. When exclusion is enabled, any registered resource whose short class name appears in the configured exclusion list is omitted from the resulting permission map. The built-in role-management resource remains present. The adapter emits one line per surviving resource, sorted by identifier.",
    "cases": [
        {
            "input": {"op": "discover_resources", "exclude_enabled": true, "exclude": ["PostResource"], "resources": [{"fqcn": "App\\Filament\\Resources\\PostResource", "model": "App\\Models\\Post"}, {"fqcn": "App\\Filament\\Resources\\BlogCategoryResource", "model": "App\\Models\\BlogCategory"}]},
            "expected_output": "resource=blog::category model=BlogCategory\nresource=role model=Role\n"
        }
    ]
}
```

*2.3 Page discovery — registered pages to sorted permission names*

Each registered standalone page contributes exactly one permission name, formed by joining the configured page action prefix and the page's short class name with an underscore. When exclusion is enabled, pages whose short class name is in the exclusion list are dropped. The adapter emits one line per surviving page permission, sorted lexicographically.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_discover_pages.json`

```json
{
    "description": "Discover the set of administrative pages and derive their permission names. Each registered page contributes a single permission name formed by joining the configured page action prefix and the page's short class name with an underscore. When exclusion is enabled, pages whose short class name is in the configured exclusion list are dropped. The adapter emits one line per page permission, sorted lexicographically.",
    "cases": [
        {
            "input": {"op": "discover_pages", "pages": ["App\\Filament\\Pages\\Settings", "App\\Filament\\Pages\\Reports", "App\\Filament\\Pages\\Dashboard"]},
            "expected_output": "page_permission=page_Reports\npage_permission=page_Settings\n"
        }
    ]
}
```

*2.4 Widget discovery — registered widgets to sorted permission names*

Each registered dashboard widget contributes exactly one permission name, formed by joining the configured widget action prefix and the widget's short class name with an underscore. When exclusion is enabled, widgets whose short class name is in the exclusion list are dropped. The adapter emits one line per surviving widget permission, sorted lexicographically.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_discover_widgets.json`

```json
{
    "description": "Discover the set of dashboard widgets and derive their permission names. Each registered widget contributes a single permission name formed by joining the configured widget action prefix and the widget's short class name with an underscore. When exclusion is enabled, widgets whose short class name is in the configured exclusion list are dropped. The adapter emits one line per widget permission, sorted lexicographically.",
    "cases": [
        {
            "input": {"op": "discover_widgets", "widgets": ["App\\Filament\\Widgets\\StatsWidget", "App\\Filament\\Widgets\\SalesChart", "App\\Filament\\Widgets\\AccountWidget"]},
            "expected_output": "widget_permission=widget_SalesChart\nwidget_permission=widget_StatsWidget\n"
        }
    ]
}
```

---

### Feature 3: Permission Generation & Super-Admin Synchronization

**As a developer**, I want generated permissions to be persisted exactly once and automatically granted to the privileged super-admin role, so the super-admin always holds the complete, current permission set without manual upkeep.

**Expected Behavior / Usage:**

Generating permissions persists each permission name into a permission store idempotently (creating it only if it does not already exist) and grants the newly materialized permissions to a super-admin role, which is itself created on demand if absent. After generation, the adapter reports the full set of stored permission names (sorted) followed by the set of permission names held by the super-admin role (sorted).

*3.1 Resource permission generation — one permission per action prefix*

For a data resource, the toolkit creates one permission per configured action prefix; each permission name is formed by joining the action prefix and the resource identifier with an underscore. All created permissions are granted to the super-admin role. The adapter emits the stored permission names (sorted) followed by the super-admin's permission names (sorted).

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_generate_resource.json`

```json
{
    "description": "Generate the full permission set for a single resource and synchronize it onto the super-admin role. For a resource the system creates one permission per configured action prefix, each named by joining the action prefix and the resource identifier with an underscore. Newly created permissions are granted to the super-admin role. The adapter emits the complete set of stored permission names (sorted) followed by the set of permission names held by the super-admin role (sorted).",
    "cases": [
        {
            "input": {"op": "generate_resource", "fqcn": "App\\Filament\\Resources\\PostResource", "model": "App\\Models\\Post", "resource_id": "post"},
            "expected_output": "permission=[a comprehensive set of CRUD action permissions including super-admin scalpers]\npermission=[a comprehensive set of CRUD action permissions including super-admin scalpers]\npermission=[a comprehensive set of CRUD action permissions including super-admin scalpers]\npermission=force_[a comprehensive set of CRUD action permissions including super-admin scalpers]\npermission=force_[a comprehensive set of CRUD action permissions including super-admin scalpers]\npermission=[a comprehensive set of CRUD action permissions including super-admin scalpers]\npermission=[a comprehensive set of CRUD action permissions including super-admin scalpers]\npermission=[a comprehensive set of CRUD action permissions including super-admin scalpers]\npermission=[a comprehensive set of CRUD action permissions including super-admin scalpers]\npermission=[a comprehensive set of CRUD action permissions including super-admin scalpers]\npermission=[a comprehensive set of CRUD action permissions including super-admin scalpers]\npermission=[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=force_[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=force_[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=[a comprehensive set of CRUD action permissions including super-admin scalpers]\nsuper_admin=[a comprehensive set of CRUD action permissions including super-admin scalpers]\n"
        }
    ]
}
```

*3.2 Resource permission generation with a custom prefix set — override the default prefixes*

A resource may declare its own action-prefix set, which overrides the global default. Only the resource's declared prefixes are used to form its permission names. The created permissions are granted to the super-admin role. The adapter emits the stored permission names (sorted) followed by the super-admin's permission names (sorted).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_generate_resource_custom_prefixes.json`

```json
{
    "description": "Generate permissions for a resource that declares its own custom action-prefix set rather than relying on the global default. When a resource opts in to a custom permission-prefix contract, only that resource's declared prefixes are used to form its permission names, overriding the global prefix list. The newly created permissions are granted to the super-admin role. The adapter emits the stored permission names (sorted) followed by the super-admin's permission names (sorted).",
    "cases": [
        {
            "input": {"op": "generate_resource", "fqcn": "App\\Filament\\Resources\\UserResource", "model": "App\\Models\\User", "resource_id": "user", "custom_prefixes": ["view", "update", "audit"]},
            "expected_output": "permission=audit_user\npermission=update_user\npermission=view_user\nsuper_admin=audit_user\nsuper_admin=update_user\nsuper_admin=view_user\n"
        }
    ]
}
```

*3.3 Page permission synchronization — register page permissions onto the super-admin role*

Given a set of page permission names, each name is created once (idempotently) in the permission store and granted to the super-admin role. The adapter emits the stored permission names (sorted) followed by the super-admin's permission names (sorted).

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_generate_page.json`

```json
{
    "description": "Register page permissions and synchronize them onto the super-admin role. Each supplied page permission name is created exactly once (idempotently) in the permission store and then granted to the super-admin role. The adapter emits the stored permission names (sorted) followed by the super-admin's permission names (sorted).",
    "cases": [
        {
            "input": {"op": "generate_page", "permissions": ["page_Settings", "page_Reports"]},
            "expected_output": "permission=page_Reports\npermission=page_Settings\nsuper_admin=page_Reports\nsuper_admin=page_Settings\n"
        }
    ]
}
```

*3.4 Widget permission synchronization — register widget permissions onto the super-admin role*

Given a set of widget permission names, each name is created once (idempotently) in the permission store and granted to the super-admin role. The adapter emits the stored permission names (sorted) followed by the super-admin's permission names (sorted).

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_generate_widget.json`

```json
{
    "description": "Register widget permissions and synchronize them onto the super-admin role. Each supplied widget permission name is created exactly once (idempotently) in the permission store and then granted to the super-admin role. The adapter emits the stored permission names (sorted) followed by the super-admin's permission names (sorted).",
    "cases": [
        {
            "input": {"op": "generate_widget", "permissions": ["widget_StatsWidget", "widget_SalesChart"]},
            "expected_output": "permission=widget_SalesChart\npermission=widget_StatsWidget\nsuper_admin=widget_SalesChart\nsuper_admin=widget_StatsWidget\n"
        }
    ]
}
```

---

### Feature 4: Action-Prefix Resolution

**As a developer**, I want to resolve which action prefixes apply to a given resource, so a resource can either inherit a sensible global default set of actions or declare its own.

**Expected Behavior / Usage:**

The set of action prefixes that drives permission generation for a resource is resolved per resource: a resource that does not declare its own prefix contract inherits the global default list, while a resource that opts in to a custom contract uses its declared list verbatim, preserving declaration order. The adapter emits one line per resolved prefix, in resolution order.

*4.1 Default prefix set — inherit the global defaults*

A resource without a custom prefix contract resolves to the global default action-prefix list, emitted in the global default order.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_prefixes_default.json`

```json
{
    "description": "Resolve the action-prefix set that applies to a given resource. When a resource does not declare its own permission-prefix contract, the global default prefix list applies; the adapter emits one line per prefix in the global default order.",
    "cases": [
        {
            "input": {"op": "resource_prefixes", "fqcn": "App\\Filament\\Resources\\PostResource", "model": "App\\Models\\Post"},
            "expected_output": "prefix=view\nprefix=view_any\nprefix=create\nprefix=update\nprefix=restore\nprefix=restore_any\nprefix=replicate\nprefix=reorder\nprefix=delete\nprefix=delete_any\nprefix=force_delete\nprefix=force_delete_any\n"
        }
    ]
}
```

*4.2 Custom prefix set — use a resource's declared prefixes*

A resource that declares its own prefix contract resolves to exactly that list, in declaration order, overriding the global default.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_prefixes_custom.json`

```json
{
    "description": "Resolve the action-prefix set for a resource that declares its own custom permission-prefix contract. When a resource opts in to a custom prefix contract, that resource's declared prefix list is used verbatim, overriding the global default; the adapter emits one line per declared prefix in the order declared.",
    "cases": [
        {
            "input": {"op": "resource_prefixes", "fqcn": "App\\Filament\\Resources\\UserResource", "model": "App\\Models\\User", "custom_prefixes": ["view", "update", "audit"]},
            "expected_output": "prefix=view\nprefix=update\nprefix=audit\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing identifier derivation, component discovery, permission generation with super-admin synchronization, and action-prefix resolution, organized into distinct logical units rather than a single file.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin, invokes the appropriate core logic, and prints the normalized, deterministic result to stdout, strictly matching the per-leaf-feature contracts above (sorted permission names / identifier mappings, or a neutral `error=<category>` line). This adapter must be logically separated from the core domain.

3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{idx:03d}.txt` containing only the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply the same ordering as used when listing global prefixes
