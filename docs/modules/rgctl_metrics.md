# rgctl.rgctl.rgctl_metrics

Collect graph-based code metrics: PageRank hotspots, community structure, and betweenness centrality.

## Synopsis

Runs `rgctl metrics` against an indexed codebase to surface which symbols carry the most structural risk (PageRank), how the codebase is modularly divided (communities), and which symbols act as architectural bridges (betweenness). Use this after `rgctl_discover` to get quantitative coupling data before a large refactor or to track health trends over time. Always returns `changed: false`.

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | str | yes | — | Absolute path to the indexed codebase |
| `metrics` | list | no | `[pagerank, communities]` | Which metrics to collect: `pagerank`, `communities`, `betweenness` |
| `top_n` | int | no | `20` | Number of top symbols to return for ranked metrics (pagerank, betweenness) |
| `rgctl_bin` | str | no | `rgctl` | Path to the rgctl binary |
| `timeout` | int | no | `120` | Timeout in seconds |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | Always `false` |
| `rgctl_metrics` | dict | Collected metrics (see sub-keys below) |
| `rgctl_metrics.pagerank_top` | list | Top N symbols by PageRank score. Each entry: `name`, `qualified_name`, `kind`, `file_path`, `pagerank` |
| `rgctl_metrics.pagerank_converged` | bool | Whether the PageRank algorithm converged |
| `rgctl_metrics.pagerank_iterations` | int | Number of iterations run |
| `rgctl_metrics.communities` | dict | Community detection summary: `count`, `modularity`, `assignments` |
| `rgctl_metrics.betweenness_top` | list | Top N symbols by betweenness centrality (only when `betweenness` is in `metrics`) |

## Notes

**What each metric means:**

| Metric | What it tells you |
|---|---|
| **PageRank** | Symbols with high scores are heavily referenced by the rest of the graph. Changing them has wide impact — treat them as change-risk hotspots |
| **Communities** | Partitions the graph into tightly-coupled clusters. High modularity (> 0.3) means well-separated modules. Low modularity signals tangled dependencies |
| **Betweenness** | Symbols that lie on many shortest paths between other symbols — architectural bridges. Removing or changing them fragments the graph |

- `pagerank` and `communities` run together in a single rgctl call; `betweenness` is computed separately and may add time on large codebases.
- `top_n` applies to both `pagerank_top` and `betweenness_top`. The full list is available via `rgctl metrics` directly if you need more entries.
- These metrics require a completed discover index. Run `rgctl_discover` before this module.

## Examples

```yaml
# Default: PageRank + community structure
- name: Collect code metrics
  rgctl.rgctl.rgctl_metrics:
    path: /opt/analysis/my-app
    top_n: 10
  register: metrics

- name: Show top change-risk symbols
  ansible.builtin.debug:
    msg: "{{ item.qualified_name }} — score {{ item.pagerank | round(6) }}"
  loop: "{{ metrics.rgctl_metrics.pagerank_top }}"

# All three metrics
- name: Full metrics suite
  rgctl.rgctl.rgctl_metrics:
    path: /opt/analysis/my-app
    metrics:
      - pagerank
      - communities
      - betweenness
    top_n: 20
  register: full_metrics

# Gate on modularity — fail if codebase is too tangled
- name: Check architectural coupling
  rgctl.rgctl.rgctl_metrics:
    path: /opt/analysis/my-app
    metrics: [communities]
  register: coupling

- name: Warn if modularity is low
  ansible.builtin.debug:
    msg: "Warning: low modularity {{ coupling.rgctl_metrics.communities.modularity }}"
  when: coupling.rgctl_metrics.communities.modularity | float < 0.3
```
