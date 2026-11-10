# rgctl.rgctl.rgctl_clones

Detect duplicate function implementations in a codebase.

## Synopsis

Finds groups of functions that are duplicates of each other using one of three matching strategies: exact (identical code hash), bloom (token-level similarity via LSH), or fragment (structural sub-function clones). Requires the codebase to be indexed with `rgctl_discover` first. Always returns `changed: false`. The module always passes `--no-write` so it never modifies the index on disk.

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | str | yes | — | Absolute path to the indexed codebase |
| `mode` | str | no | `exact` | Clone detection mode: `exact`, `bloom`, or `fragment` |
| `symbol` | str | no | null | Optional: report only the clone group containing this symbol |
| `min_loc` | int | no | `5` | Minimum function lines of code to include in results |
| `exclude` | list | no | `[]` | Path globs to exclude (e.g. `test`, `generated`) |
| `lang` | str | no | null | Language filter (e.g. `java`, `python`) |
| `threshold` | float | no | `0.85` | Minimum Jaccard similarity threshold, range [0, 1] — `bloom` mode only |
| `rgctl_bin` | str | no | `rgctl` | Path to the rgctl binary |
| `timeout` | int | no | `180` | Timeout in seconds |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | Always `false` |
| `rgctl_clones` | list | List of clone groups. Each group has `hash`, `confidence`, and `members` (list of functions with `name`, `file`, `start_line`, `end_line`, `loc`) |
| `group_count` | int | Total number of clone groups found |

## Notes

**Clone modes:**

| Mode | Type | What it finds |
|---|---|---|
| `exact` | Type-1 | Byte-identical functions (same code hash). Fast, zero false positives |
| `bloom` | Type-2 | Token-similar functions above a Jaccard threshold. Finds renamed variables, minor edits |
| `fragment` | Type-3/4 | Structural sub-function clones using SESE hammock + 1-WL canonical subgraph. Slowest but finds deep structural duplication |

- The module always adds `--no-write` — it will never update `.rgctl/clones.json` on disk.
- Exclude test and generated directories with `exclude: [test, generated]` to focus on production code.
- Use `symbol` to quickly check whether a specific function has clones without scanning the entire codebase.
- `bloom` mode with `threshold: 0.75` is a good balance between recall and precision for large codebases.

## Examples

```yaml
# Find exact clones in production code (no tests)
- name: Detect copy-pasted functions
  rgctl.rgctl.rgctl_clones:
    path: /opt/analysis/my-app
    mode: exact
    min_loc: 5
    exclude:
      - test
      - generated
  register: clones

- name: Fail if clones found
  ansible.builtin.fail:
    msg: "{{ clones.group_count }} clone group(s) detected — review rgctl_clones output"
  when: clones.group_count | int > 0

# Token-similar clones in Java files only
- name: Bloom clone scan for Java
  rgctl.rgctl.rgctl_clones:
    path: /opt/analysis/my-app
    mode: bloom
    lang: java
    threshold: 0.80
  register: bloom_clones

# Check if a specific function has clones
- name: Check processPayment for clones
  rgctl.rgctl.rgctl_clones:
    path: /opt/analysis/my-app
    symbol: processPayment
    mode: exact
  register: payment_clones
```
