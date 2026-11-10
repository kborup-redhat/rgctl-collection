# rgctl.rgctl.analyze_pipeline

Full pipeline role: clone a Git repository, index it with rgctl, run a security scan, collect code metrics, and write a report — all in one role invocation.

## Synopsis

This role orchestrates the complete analysis workflow. It is the primary entry point for both developer-machine playbooks and AAP job templates. Each step is handled by a dedicated module, so you can also run steps individually if needed.

**Pipeline steps:**
1. `rgctl_install` — install rgctl binary (local machines only, skipped by default)
2. `ansible.builtin.git` — clone the repository (skipped when `rgctl_git_url` is empty)
3. `rgctl_discover` — index the codebase
4. `rgctl_security` — run security checks (skipped when `rgctl_checks` is empty)
5. `rgctl_metrics` — collect PageRank and community metrics (skipped when `rgctl_collect_metrics: false`)
6. `rgctl_report` — write the report
7. `set_fact` — expose `rgctl_analysis` as a host fact

## Role Variables

### Required

| Variable | Description |
|---|---|
| `rgctl_dest` | Local path where the codebase lives (clone target or existing local path) |

### Git / Clone

| Variable | Default | Description |
|---|---|---|
| `rgctl_git_url` | `""` | Remote Git URL to clone. Leave empty to analyze an existing local path. |
| `rgctl_branch` | `"main"` | Branch to checkout |
| `rgctl_git_key` | `""` | SSH key path for private repos |
| `rgctl_git_token` | `""` | HTTPS token for private repos (`no_log: true`). Token is stripped from `.git/config` after clone. |
| `rgctl_git_depth` | `0` | Shallow clone depth. `0` = full history. `1` = latest snapshot only (faster). |

### Discovery

| Variable | Default | Description |
|---|---|---|
| `rgctl_force_discover` | `false` | Re-index even if the index is current |
| `rgctl_discover_timeout` | `600` | Timeout in seconds for the discover step |
| `rgctl_discover_full` | `false` | Force a full (non-incremental) pass |
| `rgctl_discover_files` | `[]` | Discover only these repo-relative file paths |
| `rgctl_discover_find_glob` | `null` | Glob filter — include only matching files |
| `rgctl_with_cfg` | `false` | Build CFG/PDG — required for `rgctl_slice`, `rgctl_inspect`, taint |
| `rgctl_with_git` | `false` | Include git co-change edges and hotspot scores |
| `rgctl_git_since` | `null` | Git window for `rgctl_with_git` (e.g. `"90.days"`) |
| `rgctl_with_security` | `false` | Kantra security rule evaluation during discover |
| `rgctl_with_taint` | `false` | Extra taint rule pack during discover |
| `rgctl_taint_rules` | `null` | Path to taint rules YAML (with `rgctl_with_taint`) |
| `rgctl_with_ast_skeleton` | `false` | AST skeleton pass |
| `rgctl_with_dfg_loops` | `false` | Data-flow graph loop analysis |
| `rgctl_with_harmonic` | `false` | Harmonic centrality scores |
| `rgctl_with_universe` | `false` | Universe-wide scan mode |
| `rgctl_with_limits` | `null` | Resource constraints, e.g. `"max-mem-mb=2048,threads=2"` |
| `rgctl_scip` | `null` | Path to SCIP protobuf for call-edge upgrade |
| `rgctl_write_json_graph` | `false` | Write JSON graph sidecar |
| `rgctl_export_migration_hints` | `false` | Export migration hints sidecar |
| `rgctl_with_kantra` | `false` | Enable Kantra rule integration |
| `rgctl_kantra_rules` | `null` | Path to Kantra rules directory |
| `rgctl_kantra_catalog` | `null` | Path to Kantra ruleset catalog |
| `rgctl_kantra_target` | `null` | Kantra target name |
| `rgctl_kantra_index_only` | `false` | Index Kantra rules without running evals |

### Security

| Variable | Default | Description |
|---|---|---|
| `rgctl_checks` | `[]` | Checks to run: `vuln_analyze`, `deps_check`, `taint` |
| `rgctl_osv_file` | `""` | Path to OSV advisory JSON (required for `vuln_analyze` / `deps_check`) |
| `rgctl_sink_symbols` | `[]` | Sink symbols for taint analysis |
| `rgctl_taint_depth` | `8` | Max call depth for taint |
| `rgctl_severity_threshold` | `medium` | Minimum severity for `above_threshold_count` |
| `rgctl_scan_timeout` | `300` | Timeout per security check |

### Metrics

| Variable | Default | Description |
|---|---|---|
| `rgctl_collect_metrics` | `true` | Whether to run the metrics step |
| `rgctl_metrics` | `[pagerank, communities]` | Metrics to collect |
| `rgctl_metrics_top_n` | `20` | Top N symbols in PageRank output |
| `rgctl_metrics_timeout` | `120` | Timeout for metrics collection |

### Report

| Variable | Default | Description |
|---|---|---|
| `rgctl_report_dest` | `"{{ rgctl_dest }}/rgctl-report.json"` | Report file path |
| `rgctl_report_format` | `json` | Output format: `json`, `markdown`, or `html` |

### Runtime / Binary

| Variable | Default | Description |
|---|---|---|
| `rgctl_manage_install` | `false` | Install rgctl at play time (local machines). Set `false` for AAP EE. |
| `rgctl_version` | `"latest"` | rgctl version to install (when `rgctl_manage_install: true`) |
| `rgctl_install_path` | `/usr/local/bin` | Binary install directory |
| `rgctl_bin` | `rgctl` | Path or name of the rgctl binary |

## Facts Set

After the role completes, `rgctl_analysis` is available as a host fact:

```yaml
rgctl_analysis:
  index:
    path: /tmp/my-app
    files_indexed: 99
    nodes: 4654
    edges: 10593
    duration_ms: 877
    index_path: /tmp/my-app/.rgctl
  findings:
    - check: deps_check
      severity: low
      verdict: not_affected
      osv_id: GHSA-36p3-wjmg-h94x
      ...
  above_threshold_count: 0
  metrics:
    pagerank_top: [...]
    pagerank_converged: false
    communities:
      count: 4275
      modularity: 0.637
      assignments: 4654
  report_path: /tmp/my-app/rgctl-report.json
```

## Notes

- **AAP usage:** Keep `rgctl_manage_install: false` (the default). Build and deploy the included `execution-environment/` image instead. The EE bakes rgctl v0.4.26 at image build time.
- **Local-path mode:** Set `rgctl_git_url: ""` to skip the clone step and analyze an already-present local directory.
- **Token security:** When `rgctl_git_token` is set, the clone task runs with `no_log: true`, and the token is removed from `.git/config` immediately after clone.
- **Security scans:** `vuln_analyze` and `deps_check` require an OSV advisory JSON file. Download from `https://api.osv.dev/v1/vulns/<ID>`. The role does not download it automatically.
- **Idempotency:** The discover step checks `rgctl status` first and skips re-indexing if the index is current. The report step uses a content-hash comparison and only writes when the content changes.

## Examples

### Minimal — analyze a public repo (no security scan)

```yaml
- hosts: localhost
  roles:
    - role: rgctl.rgctl.analyze_pipeline
      vars:
        rgctl_git_url: "https://github.com/spring-projects/spring-petclinic"
        rgctl_dest: /tmp/analysis/spring-petclinic
        rgctl_git_depth: 1
        rgctl_report_format: html
        rgctl_report_dest: /tmp/analysis/report.html
```

### Full pipeline with Spring4Shell check

```yaml
- hosts: localhost
  roles:
    - role: rgctl.rgctl.analyze_pipeline
      vars:
        rgctl_git_url: "https://github.com/my-org/my-spring-app"
        rgctl_dest: /tmp/analysis/my-app
        rgctl_git_token: "{{ vault_github_token }}"
        rgctl_git_depth: 1
        rgctl_checks: [deps_check, vuln_analyze]
        rgctl_osv_file: /tmp/advisories/spring4shell.json
        rgctl_severity_threshold: medium
        rgctl_report_format: html
        rgctl_report_dest: /tmp/analysis/report.html

  post_tasks:
    - name: Fail if vulnerable
      ansible.builtin.fail:
        msg: "{{ rgctl_analysis.above_threshold_count }} finding(s) above threshold"
      when: rgctl_analysis.above_threshold_count | int > 0
```

### Local path — analyze without cloning

```yaml
- hosts: localhost
  roles:
    - role: rgctl.rgctl.analyze_pipeline
      vars:
        rgctl_git_url: ""
        rgctl_dest: /home/dev/projects/my-app
        rgctl_collect_metrics: true
        rgctl_metrics: [pagerank, communities, betweenness]
        rgctl_report_format: markdown
        rgctl_report_dest: /home/dev/projects/my-app/rgctl-report.md
```

### AAP job template (EE-based)

```yaml
- hosts: all
  roles:
    - role: rgctl.rgctl.analyze_pipeline
      vars:
        rgctl_manage_install: false   # rgctl is in the EE image
        rgctl_git_url: "{{ git_url }}"
        rgctl_dest: "/tmp/analysis/{{ job_id }}"
        rgctl_git_token: "{{ scm_credential }}"
        rgctl_checks: [deps_check, vuln_analyze]
        rgctl_osv_file: "{{ osv_advisory_path }}"
        rgctl_report_format: json
```
