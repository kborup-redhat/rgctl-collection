# rgctl.rgctl.rgctl_discover

Index a codebase with rgctl to build its code knowledge graph.

## Synopsis

Runs `rgctl discover` against a local codebase path, building a graph of symbols and their relationships. Must be run before any query or analysis modules. Idempotent — calls `rgctl status` first and skips indexing if the index is already current (no dirty files, `index_current: true`). Large repos may take several minutes; configure `timeout` accordingly.

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | str | **yes** | — | Absolute path to the codebase root to index. |
| `index_path` | str | no | `<path>/.rgctl` | Override the default index storage directory. Must match the value used in subsequent modules. |
| `force` | bool | no | `false` | Re-index even if the index is current. Use when you want to guarantee a fresh index. |
| `timeout` | int | no | `600` | Timeout in seconds for the discover command. Increase for large repos (Linux kernel: ~48s on M3 Pro, may be longer on slower hosts). |
| `rgctl_bin` | str | no | `rgctl` | Path to the rgctl binary. Override if not in PATH. |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | `true` if the codebase was (re)indexed. `false` if the index was already current. |
| `rgctl_index` | dict | Index summary. See fields below. |
| `rgctl_index.path` | str | Indexed codebase path. |
| `rgctl_index.files_indexed` | int | Files included in the graph. |
| `rgctl_index.nodes` | int | Graph nodes generated. |
| `rgctl_index.edges` | int | Graph edges generated. |
| `rgctl_index.duration_ms` | int | Indexing duration in milliseconds (0 on skip). |
| `rgctl_index.index_path` | str | Where the index is stored on disk. |

## Notes

- **Idempotency:** The module calls `rgctl status -f json` before every run. If `status == "ok"`, `index_current == true`, and `dirty_files == 0`, it exits without running discover and returns `changed: false`. On a skip, `nodes` and `edges` are populated from the status response.
- **Taint analysis prerequisite:** If you plan to run taint analysis (`rgctl_security` with `taint` check), set `rgctl_with_cfg: true` in the `analyze_pipeline` role, which passes `--with-cfg` to discover. This is slower but required.
- The index is stored in a hidden `.rgctl/` directory inside the repo (or at `index_path` if overridden).

## Examples

```yaml
# Basic indexing
- name: Index codebase
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
  register: index_result

# Force re-index (e.g. after a large merge)
- name: Force full re-index
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
    force: true
    timeout: 900

# Custom index location (useful when the codebase is read-only)
- name: Index with custom index path
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
    index_path: /var/rgctl-indexes/myapp

# Use result in subsequent tasks
- name: Show graph size
  ansible.builtin.debug:
    msg: "{{ index_result.rgctl_index.nodes }} nodes, {{ index_result.rgctl_index.edges }} edges"
```
