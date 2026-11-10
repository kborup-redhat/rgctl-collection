# rgctl.rgctl.rgctl_find

Search for symbols in an indexed codebase by name, type, or language.

## Synopsis

Queries the rgctl graph index for symbols matching a name glob, type filter, or language. Returns a list of matching entities with their qualified names, file paths, and line numbers. Requires `rgctl_discover` to have been run first. Always returns `changed: false` — read-only.

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | str | **yes** | — | Absolute path to the indexed codebase. |
| `pattern` | str | no | `""` | Name or glob pattern. Supports `*` wildcard (e.g. `Owner`, `User*`, `*Service*`). Omit to list all symbols of a given type. |
| `symbol_type` | str | no | `null` | Filter by node type: `function`, `class`, `import`, `annotation`, `variable`, or others. |
| `file_glob` | str | no | `null` | Path glob to restrict results to specific files (e.g. `*/owner/*.java`). |
| `lang` | str | no | `null` | Language filter: `java`, `rust`, `python`, `typescript`, etc. |
| `scope` | str | no | `null` | Qualified name prefix scope (e.g. `org.springframework.samples`). |
| `limit` | int | no | `50` | Maximum number of results to return. |
| `exact` | bool | no | `false` | Disable glob — match only the exact name provided. |
| `rgctl_bin` | str | no | `rgctl` | Path to the rgctl binary. |
| `timeout` | int | no | `60` | Timeout in seconds. |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | Always `false`. |
| `rgctl_find_results` | list | List of matching symbol dicts. Each has `id`, `name`, `qualified_name`, `type`, `file`, `line`. |
| `total` | int | Total matches in the graph (may exceed `limit`). |

## Notes

- If `pattern` resolves to an ambiguous symbol name and `exact: true` is set, all matches are returned. Use `scope` or `file_glob` to narrow results.
- `total` may be larger than `rgctl_find_results` length when results are truncated by `limit`.
- Use the `id` or `qualified_name` from results to pass to `rgctl_callers`, `rgctl_blast_radius`, etc.

## Examples

```yaml
# Find a class by exact name
- name: Find Owner class
  rgctl.rgctl.rgctl_find:
    path: /opt/myapp
    pattern: Owner
    symbol_type: class
  register: owners

# Glob: find all service classes
- name: Find all *Service classes
  rgctl.rgctl.rgctl_find:
    path: /opt/myapp
    pattern: "*Service*"
    symbol_type: class
    limit: 100

# Find all functions in a specific package scope
- name: Find controller functions
  rgctl.rgctl.rgctl_find:
    path: /opt/myapp
    symbol_type: function
    scope: org.springframework.samples.petclinic.owner
    limit: 200

# Use result to drive subsequent analysis
- name: Get blast radius for each found symbol
  rgctl.rgctl.rgctl_blast_radius:
    path: /opt/myapp
    symbol: "{{ item.name }}"
    class_name: "{{ item.qualified_name.split('.')[-2] }}"
  loop: "{{ owners.rgctl_find_results }}"
```
