# rgctl.rgctl.rgctl_relations

Traverse typed edges in the code knowledge graph.

## Synopsis

Returns edges of a specific type between symbols — for example all `extends` relationships from a class, all `calls` edges into a function, or a seedless scan of every `annotatedwith` edge in the codebase. Requires the codebase to be indexed with `rgctl_discover` first. Always returns `changed: false`.

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | str | yes | — | Absolute path to the indexed codebase |
| `edge` | str | yes | — | Edge type to traverse (see Notes for full list) |
| `symbol` | str | no | null | Seed symbol. Omit for a seedless scan over all edges of that type |
| `direction` | str | no | `out` | Traversal direction: `in`, `out`, or `both` |
| `depth` | int | no | `1` | Traversal depth |
| `limit` | int | no | `50` | Maximum results |
| `class_name` | str | no | null | Class/namespace filter to disambiguate overloads |
| `file` | str | no | null | Source file path filter |
| `line` | int | no | null | Definition line disambiguator |
| `rgctl_bin` | str | no | `rgctl` | Path to the rgctl binary |
| `timeout` | int | no | `60` | Timeout in seconds |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | Always `false` |
| `rgctl_relations` | list | List of matching edge dicts |
| `total` | int | Total edge count |
| `target` | dict | Resolved seed symbol (when `symbol` is provided) |

## Notes

**Common edge types:**

| Edge | Meaning |
|---|---|
| `calls` | Function A calls function B |
| `extends` | Class A extends class B |
| `implements` | Class A implements interface B |
| `overrides` | Method A overrides method B |
| `uses` | Symbol A uses symbol B |
| `cochangeswith` | A and B frequently change together (git history) |
| `annotatedwith` | Symbol carries a specific annotation |
| `exposesroute` | Function exposes an HTTP route |
| `injects` | A is injected into B (DI frameworks) |

- Use `direction: in` to find what uses a symbol, `direction: out` for what it uses.
- Omitting `symbol` performs a codebase-wide scan for all edges of the given type. Use `limit` to control result count.
- Ambiguous symbols return an error; use `class_name`, `file`, or `line` to disambiguate.

## Examples

```yaml
# Find all classes that Owner extends
- name: Get Owner inheritance
  rgctl.rgctl.rgctl_relations:
    path: /opt/analysis/my-app
    symbol: Owner
    edge: extends
    direction: out
  register: inheritance

# Find everything that calls a function (incoming direction)
- name: Who calls processPayment
  rgctl.rgctl.rgctl_relations:
    path: /opt/analysis/my-app
    symbol: processPayment
    class_name: PaymentService
    edge: calls
    direction: in
    depth: 2
  register: callers

# Seedless scan: all REST endpoint exposures in the codebase
- name: List all exposed routes
  rgctl.rgctl.rgctl_relations:
    path: /opt/analysis/my-app
    edge: exposesroute
    limit: 100
  register: routes
```
