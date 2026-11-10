# rgctl.rgctl.rgctl_discover

Index a codebase with rgctl to build its code knowledge graph.

## Synopsis

Runs `rgctl discover` against a local codebase path, building a graph of symbols and their relationships. Must be run before any query or analysis modules. Idempotent — calls `rgctl status` first and skips indexing if the index is already current. Supports optional analysis passes (CFG/PDG, git co-change, security rules, taint, harmonic centrality, and more) that enrich the graph for deeper analysis.

## Parameters

### Core

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | str | **yes** | — | Absolute path to the codebase root to index. |
| `index_path` | str | no | `<path>/.rgctl` | Override the default index storage directory. Must match the value used in subsequent modules. |
| `force` | bool | no | `false` | Re-index even if the index is current. |
| `full` | bool | no | `false` | Force a full (non-incremental) discovery pass. |
| `timeout` | int | no | `600` | Timeout in seconds. Increase for large repos or when enabling slow passes (`with_cfg`, `with_harmonic`). |
| `rgctl_bin` | str | no | `rgctl` | Path to the rgctl binary. |

### Filtering

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `files` | list | no | `[]` | Discover only these repo-relative file paths. Comma-joined and passed as `--files`. |
| `find_glob` | str | no | `null` | Glob filter — include only matching files (e.g. `**/model/**`). Passed as `--find`. |

### Analysis Passes

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `with_cfg` | bool | no | `false` | Build per-function CFG, dominators, and PDG into `.rgctl/analysis/`. **Required** for `rgctl_slice`, `rgctl_inspect`, and taint analysis. Slower on large repos. |
| `with_git` | bool | no | `false` | Include git co-change edges and hotspot scores. |
| `git_since` | str | no | `null` | Git window for `--with-git` (e.g. `"90.days"`, `"2024-01-01"`). Only effective when `with_git: true`. |
| `with_security` | bool | no | `false` | Run Kantra security rule evaluation during discover. Results appear in `rgctl status` as `kantra_findings`. |
| `with_taint` | bool | no | `false` | Include extra taint rule pack during discover. |
| `taint_rules` | str | no | `null` | Path to taint rules YAML file or directory. Used with `with_taint`. |
| `with_ast_skeleton` | bool | no | `false` | Build AST skeleton pass. |
| `with_dfg_loops` | bool | no | `false` | Include data-flow graph loop analysis. |
| `with_harmonic` | bool | no | `false` | Compute harmonic centrality scores. |
| `with_universe` | bool | no | `false` | Enable universe-wide scan mode. |

### Resources and External Data

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `with_limits` | str | no | `null` | Resource constraints for containers/AAP EEs. Format: `"max-mem-mb=4096,threads=2"`. Pass an empty string `""` to enable limits mode with defaults. |
| `scip` | str | no | `null` | Path to a SCIP protobuf index (`.scip`) to upgrade ambiguous call edges with compiler-exact resolution. |
| `write_json_graph` | bool | no | `false` | Write a JSON graph sidecar alongside the binary snapshot. |
| `export_migration_hints` | bool | no | `false` | Export migration hints sidecar. |

### Kantra Integration

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `with_kantra` | bool | no | `false` | Enable Kantra rule integration during discover. |
| `kantra_rules` | str | no | `null` | Path to Kantra rules directory (`ruleset.yaml` + `*.yaml`). |
| `kantra_catalog` | str | no | `null` | Path to Kantra ruleset catalog root. |
| `kantra_target` | str | no | `null` | Kantra target name to run. |
| `kantra_index_only` | bool | no | `false` | Index Kantra rules into the graph without running violation eval. |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | `true` if the codebase was (re)indexed. `false` if the index was already current. |
| `cfg_built` | bool | `true` if CFG/PDG artifacts were built in this run (or already present when skipped). |
| `rgctl_index` | dict | Index summary. |
| `rgctl_index.path` | str | Indexed codebase path. |
| `rgctl_index.files_indexed` | int | Files included in the graph. |
| `rgctl_index.nodes` | int | Graph nodes generated. |
| `rgctl_index.edges` | int | Graph edges generated (more with `with_git` co-change edges). |
| `rgctl_index.duration_ms` | int | Indexing duration in milliseconds (`0` on skip). |
| `rgctl_index.index_path` | str | Where the index is stored on disk. |

## Notes

- **Idempotency:** Calls `rgctl status -f json` before every run. Skips if `status == "ok"`, `index_current == true`, `dirty_files == 0`, and CFG is already built (when `with_cfg: true`). Returns `changed: false` on skip.
- **CFG prerequisite:** `rgctl_slice` and `rgctl_inspect` require `with_cfg: true`. The module tracks `cfg_built` and will NOT skip a run where `with_cfg: true` but CFG has not yet been built.
- **Analysis pass labels:** The `msg` field lists active passes, e.g. `"Codebase indexed (with git, security, harmonic)"`.
- **git co-change edges:** `with_git` adds co-change edges based on files that frequently change together in git history. These extra edges increase the graph edge count noticeably.
- **AAP resource limits:** Use `with_limits` to prevent OOM kills inside constrained execution environment containers.

## Examples

```yaml
# Basic idempotent indexing
- name: Index codebase
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
  register: index_result

# Full index with CFG (required for slice and inspect)
- name: Index with CFG/PDG
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
    with_cfg: true
    timeout: 1200
  register: index_result

# Git co-change edges + security rules, last 60 days
- name: Index with git and security
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
    with_git: true
    git_since: "60.days"
    with_security: true
    with_harmonic: true
  register: index_result

# Discover only files in a specific package
- name: Partial index — owner package only
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
    find_glob: "**/owner/**"
    force: true

# Specific files only (useful in CI after detecting changed files)
- name: Index only changed files
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
    files:
      - src/main/java/com/example/UserService.java
      - src/main/java/com/example/UserController.java
    force: true

# Resource-constrained discover for AAP EE containers
- name: Index with memory limit
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
    with_limits: "max-mem-mb=2048,threads=2"

# Kantra rule integration
- name: Index with Kantra rules
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
    with_kantra: true
    kantra_rules: /opt/kantra-rules/

# Combined — full analysis suite
- name: Full analysis index
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
    with_cfg: true
    with_git: true
    git_since: "90.days"
    with_security: true
    with_taint: true
    with_harmonic: true
    write_json_graph: true
    timeout: 1800

- name: Show graph size after indexing
  ansible.builtin.debug:
    msg: >-
      {{ index_result.rgctl_index.nodes }} nodes,
      {{ index_result.rgctl_index.edges }} edges,
      CFG built: {{ index_result.cfg_built }}
```
