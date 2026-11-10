# rgctl.rgctl.rgctl_callees

Get the outgoing callees of a symbol (what this function calls).

## Synopsis

Traverses the CALLS edges in the rgctl graph to find all symbols called by the given symbol, up to a configurable depth. Useful for understanding a function's dependencies and for tracing execution paths. Requires `rgctl_discover` to have run first. Always returns `changed: false` — read-only.

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | str | **yes** | — | Absolute path to the indexed codebase. |
| `symbol` | str | **yes** | — | Symbol name, UUID, or fully-qualified name. |
| `depth` | int | no | `1` | Number of call hops to traverse outward. `1` = direct callees only. |
| `class_name` | str | no | `null` | Class or namespace to disambiguate overloaded method names. |
| `file` | str | no | `null` | Source file path filter to disambiguate. |
| `line` | int | no | `null` | 1-based definition line to disambiguate overloads. |
| `limit` | int | no | `50` | Maximum results. |
| `rgctl_bin` | str | no | `rgctl` | Path to the rgctl binary. |
| `timeout` | int | no | `60` | Timeout in seconds. |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | Always `false`. |
| `rgctl_callees` | list | List of callee symbol dicts. Each has `id`, `name`, `qualified_name`, `type`, `file`, `line`. |
| `total` | int | Number of callees returned. |

## Notes

- **Ambiguous symbols:** If `symbol` matches multiple functions, the module fails with an `AMBIGUOUS_SYMBOL` error. Use `class_name`, `file`, or `line` to disambiguate.
- **Depth > 1:** Transitively follows outgoing calls. Result size can be large for functions with broad call trees — set `limit` to cap it.
- **vs. callers:** `rgctl_callers` = incoming edges (who calls me). `rgctl_callees` = outgoing edges (who I call). Both use the same disambiguation options.

## Examples

```yaml
# What does processCreationForm call?
- name: Get callees of processCreationForm
  rgctl.rgctl.rgctl_callees:
    path: /opt/myapp
    symbol: processCreationForm
    class_name: OwnerController
  register: callees_result

- name: Show callees
  ansible.builtin.debug:
    msg: "{{ callees_result.rgctl_callees | map(attribute='qualified_name') | list }}"

# Deeper traversal — what does the whole call tree look like?
- name: Call tree (3 hops)
  rgctl.rgctl.rgctl_callees:
    path: /opt/myapp
    symbol: handleRequest
    class_name: ApiController
    depth: 3
    limit: 500

# Fail the play if a function calls any database layer directly
- name: Check for direct DB calls from controller
  rgctl.rgctl.rgctl_callees:
    path: /opt/myapp
    symbol: processForm
    class_name: UserController
  register: direct_calls

- name: Fail if repository is called directly from controller
  ansible.builtin.fail:
    msg: "Controller calls repository directly: {{ item.qualified_name }}"
  loop: "{{ direct_calls.rgctl_callees }}"
  when: "'Repository' in item.qualified_name"
```
