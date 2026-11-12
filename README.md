# rgctl.rgctl Ansible Collection

Ansible collection for automating code knowledge graph analysis with [rgctl](https://github.com/rgctl/rgctl).

rgctl builds a rich graph of code relationships — 30+ typed edges (calls, extends, injects, exposes routes, co-changes, …) across 60+ languages. This collection exposes those capabilities as idiomatic Ansible modules so you can automate code analysis in playbooks, CI pipelines, and AAP job templates.

## Requirements

- ansible-core >= 2.15
- rgctl v0.4.26+ on the target node (or baked into the EE image)
- Python 3.9+ on the target node

## Installation

```bash
ansible-galaxy collection install rgctl.rgctl
```

Or from a local build:

```bash
ansible-galaxy collection install rgctl-rgctl-0.1.0.tar.gz
```

## Modules

### Setup & Lifecycle

| Module | Description |
|---|---|
| `rgctl_install` | Install rgctl binary on local machines (idempotent version check) |
| `rgctl_discover` | Index a codebase — 24 flags covering CFG/PDG, git co-change, security, taint, Kantra, harmonic, resource limits |
| `rgctl_update` | Incremental index update for changed files |
| `rgctl_diff` | Diff two graph snapshots (base vs head branch) |
| `rgctl_semantic_index` | Build the semantic search index for NL queries |

### Query

| Module | Description |
|---|---|
| `rgctl_find` | Search symbols by name/glob/type/language |
| `rgctl_callers` | Incoming callers of a symbol (up to N hops) |
| `rgctl_callees` | Outgoing callees of a symbol |
| `rgctl_relations` | Traverse typed edges (calls, extends, implements, cochangeswith, …) |
| `rgctl_inventory` | Aggregate symbol/edge counts by type, language, file, community |

### Analysis

| Module | Description |
|---|---|
| `rgctl_blast_radius` | Transitive upstream impact zone — "what breaks if I change this?" |
| `rgctl_clones` | Duplicate function detection (exact, bloom LSH, structural) |
| `rgctl_metrics` | PageRank hotspots, community detection, betweenness centrality |
| `rgctl_slice` | Backward/forward program slice at a file:line:variable criterion |
| `rgctl_inspect` | CFG, PDG, or dominator tree for a function |
| `rgctl_semantic` | Natural-language semantic search over function symbols |

### Security

| Module | Description |
|---|---|
| `rgctl_security` | OSV advisory checks (`vuln_analyze`, `deps_check`) and taint analysis |

### Policy & Review

| Module | Description |
|---|---|
| `rgctl_check` | CI policy gateway — runs a policy file and returns violations |
| `rgctl_review` | PR call-path diff between two graph snapshots |

### Output

| Module | Description |
|---|---|
| `rgctl_report` | Write analysis reports — JSON, Markdown, or HTML (with embedded Mermaid graphs) |
| `rgctl_graph` | Generate Mermaid flowchart diagrams from callers/blast_radius/relations data |

## Role

### `rgctl.rgctl.analyze_pipeline`

Orchestrates the full analysis pipeline:

1. Install rgctl *(local machines only)*
2. Clone a Git repository *(skip by leaving `rgctl_git_url` empty)*
3. Index the codebase with all requested discover passes
4. Run security scans against OSV advisories
5. Collect code metrics (PageRank, communities)
6. Write a report (JSON / Markdown / HTML)
7. Expose `rgctl_analysis` as a host fact for downstream tasks

## Quick Start

### Local machine

```bash
# Install rgctl
ansible-playbook rgctl.rgctl.install

# Run the full analysis pipeline against a Java repo
cat > analysis.yml << 'EOF'
- hosts: localhost
  roles:
    - role: rgctl.rgctl.analyze_pipeline
      vars:
        rgctl_git_url: "https://github.com/spring-projects/spring-petclinic"
        rgctl_dest: /tmp/analysis/spring-petclinic
        rgctl_git_depth: 1
        rgctl_with_git: true
        rgctl_with_security: true
        rgctl_report_format: html
        rgctl_report_dest: /tmp/analysis/report.html
EOF
ansible-playbook analysis.yml
```

### Security scan against a specific advisory (Spring4Shell)

```yaml
- hosts: localhost
  roles:
    - role: rgctl.rgctl.analyze_pipeline
      vars:
        rgctl_git_url: "https://github.com/my-org/my-spring-app"
        rgctl_dest: /tmp/analysis/my-app
        rgctl_git_token: "{{ vault_github_token }}"
        rgctl_checks: [deps_check, vuln_analyze]
        rgctl_osv_file: /tmp/advisories/GHSA-36p3-wjmg-h94x.json
        rgctl_severity_threshold: medium
        rgctl_report_format: html

  post_tasks:
    - ansible.builtin.fail:
        msg: "{{ rgctl_analysis.above_threshold_count }} finding(s) above threshold"
      when: rgctl_analysis.above_threshold_count | int > 0
```

### Query modules

```yaml
- hosts: localhost
  tasks:
    - name: Find all service classes
      rgctl.rgctl.rgctl_find:
        path: /opt/myapp
        pattern: "*Service*"
        symbol_type: class
      register: services

    - name: Blast radius of a critical method
      rgctl.rgctl.rgctl_blast_radius:
        path: /opt/myapp
        symbol: processPayment
        class_name: PaymentService
      register: blast

    - name: Generate call graph
      rgctl.rgctl.rgctl_graph:
        path: /opt/myapp
        dest: /tmp/callers.mmd
        data: "{{ blast }}"
        data_type: blast_radius
        title: "Impact of processPayment"
```

### CFG and program slicing

```yaml
- name: Index with CFG/PDG
  rgctl.rgctl.rgctl_discover:
    path: /opt/myapp
    with_cfg: true

- name: Inspect CFG of a function
  rgctl.rgctl.rgctl_inspect:
    path: /opt/myapp
    symbol: processPayment
    class_name: PaymentService
    subcommand: cfg

- name: Backward slice — what influences this variable?
  rgctl.rgctl.rgctl_slice:
    path: /opt/myapp
    file: src/main/java/PaymentService.java
    line: 142
    variable: amount
    direction: backward
```

## AAP (Ansible Automation Platform)

Build the included Execution Environment — it bakes rgctl into the image so no runtime download is needed:

```bash
cd execution-environment/
ansible-builder build -t rgctl-ee:0.4.26 -f execution-environment.yml
```

Push to your registry and configure in AAP Controller. Set `rgctl_manage_install: false` (the default) in job templates.

## Documentation

Full module and role reference: [`docs/`](docs/)

- [Module index](docs/index.md)
- [analyze_pipeline role](docs/roles/analyze_pipeline.md)

## License

Apache-2.0
