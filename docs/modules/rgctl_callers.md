# rgctl.rgctl.rgctl_callers

Get the incoming callers of a symbol (who calls this function).

## Synopsis

Traverses the CALLS edges in the rgctl graph to find all symbols that call the given symbol, up to a configurable depth. Useful for understanding coupling and the blast radius of a potential change. Requires `rgctl_discover` to have run first. Always returns `changed: false` — read-only.

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | str | **yes** | — | Absolute path to the indexed codebase. |
| `symbol` | str | **yes** | — | Symbol name, UUID, or fully-qualified name. |
| `depth` | int | no | `1` | Number of call hops to traverse. `1` = direct callers only. `2` = callers of callers, etc. |
| `class_name` | str | no | `null` | Class or namespace to disambiguate overloaded method names. Required when multiple methods share the same name. |
| `file` | str | no | `null` | Source file path filter to disambiguate. |
| `line` | int | no | `null` | 1-based definition line to disambiguate overloads. |
| `limit` | int | no | `50` | Maximum results. |
| `rgctl_bin` | str | no | `rgctl` | Path to the rgctl binary. |
| `timeout` | int | no | `60` | Timeout in seconds. |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | Always `false`. |
| `rgctl_callers` | list | List of caller symbol dicts. Each has `id`, `name`, `qualified_name`, `type`, `file`, `line`. |
| `total` | int | Number of callers returned. |

## Notes

- **Ambiguous symbols:** If `symbol` matches multiple functions (overloads, same name in different classes), rgctl returns an `AMBIGUOUS_SYMBOL` error and the module fails. Use `class_name`, `file`, or `line` to disambiguate. Run `rgctl_find` first to identify the right symbol.
- **Depth > 1:** With `depth: 2`, the result includes all callers of callers (transitive). Result size grows exponentially — use `limit` to cap it.
- **vs. blast_radius:** `rgctl_callers` returns individual caller symbols. `rgctl_blast_radius` returns a scored impact analysis with topology and gatekeeping. Use `callers` for lightweight queries, `blast_radius` for full impact assessment.

## Examples

```yaml
# Direct callers of a unique function
- name: Who calls getName?
  rgctl.rgctl.rgctl_callers:
    path: /opt/myapp
    symbol: getName
    class_name: NamedEntity
  register: callers_result

# Two hops: callers and their callers
- name: Transitive callers (2 hops)
  rgctl.rgctl.rgctl_callers:
    path: /opt/myapp
    symbol: processPayment
    class_name: PaymentService
    depth: 2
    limit: 200

# Use result to list affected files
- name: Show affected files
  ansible.builtin.debug:
    msg: "{{ callers_result.rgctl_callers | map(attribute='file') | unique | list }}"
```
