# rgctl.rgctl.rgctl_blast_radius

Compute the blast radius — transitive upstream impact zone — for a function symbol.

## Synopsis

Answers "what breaks if I change this function?" by walking every incoming call path transitively and returning the full set of affected symbols, their distance buckets, and an impact score. Run this before modifying a function to understand risk. Requires the codebase to be indexed with `rgctl_discover` first. Always returns `changed: false`.

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | str | yes | — | Absolute path to the indexed codebase |
| `symbol` | str | yes | — | Function symbol name, UUID, or FQN |
| `class_name` | str | no | null | Class/namespace filter to disambiguate overloads |
| `file` | str | no | null | Source file path filter |
| `line` | int | no | null | Definition line disambiguator |
| `depth` | int | no | null | Limit traversal to N incoming call hops. Default: full transitive closure |
| `summary` | bool | no | `false` | Return compact summary (score + buckets) instead of full topology |
| `classify_boundary` | bool | no | `false` | Label impact nodes with boundary types (REST, messaging, …) |
| `rgctl_bin` | str | no | `rgctl` | Path to the rgctl binary |
| `timeout` | int | no | `120` | Timeout in seconds |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | Always `false` |
| `impact_score` | float | Numeric blast radius score from rgctl (higher = riskier change) |
| `rgctl_blast_radius` | dict | Full result containing `target`, `metrics`, `topology`, and `gatekeeping` sub-keys |
| `rgctl_blast_radius.target` | dict | Resolved function symbol (name, file, signature, language) |
| `rgctl_blast_radius.metrics` | dict | `impact_zone_size`, `direct_callers_count`, `score` |
| `rgctl_blast_radius.topology` | dict | `direct_callers` list with FQN and file for each |
| `rgctl_blast_radius.gatekeeping` | dict | Policy violations and boundary handoffs (if policy file configured) |

## Notes

- **Requires a function symbol**, not a class. `getName` works; `Owner` does not.
- If the symbol name matches multiple functions, the module fails with a `NOT_FOUND` or `AMBIGUOUS_SYMBOL` error including a `recovery_command` hint. Use `class_name`, `file`, or `line` to disambiguate.
- `summary: true` returns a compact result (score, distance buckets, top files) suitable for a quick gate check without loading the full topology list.
- `classify_boundary: true` labels impact nodes as `REST_ENDPOINT`, `MESSAGING`, etc. — useful for understanding which APIs are affected.
- Large codebases with high-fan-in functions may take longer; increase `timeout` if needed.

## Examples

```yaml
# Basic blast radius — full topology
- name: Assess impact of changing getName
  rgctl.rgctl.rgctl_blast_radius:
    path: /opt/analysis/my-app
    symbol: getName
    class_name: NamedEntity
  register: blast

- name: Fail if impact score is too high
  ansible.builtin.fail:
    msg: "High-risk change — blast radius score {{ blast.impact_score }}"
  when: blast.impact_score | float > 50

# Summary mode for a quick CI gate
- name: Quick blast radius check
  rgctl.rgctl.rgctl_blast_radius:
    path: /opt/analysis/my-app
    symbol: processPayment
    class_name: PaymentService
    summary: true
  register: blast_summary

# With boundary classification for API impact
- name: Check which REST endpoints are affected
  rgctl.rgctl.rgctl_blast_radius:
    path: /opt/analysis/my-app
    symbol: validateUser
    class_name: AuthService
    classify_boundary: true
    depth: 5
  register: blast_boundaries
```
