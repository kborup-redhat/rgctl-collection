# rgctl.rgctl Ansible Collection

Ansible collection for automating code knowledge graph analysis with [rgctl](https://github.com/rgctl/rgctl).

## Overview

rgctl builds a rich graph of code relationships — 30+ typed edges (calls, extends, injects, exposes routes, co-changes, …) across 60+ languages. This collection exposes those capabilities as idiomatic Ansible modules so you can automate code analysis in playbooks, CI pipelines, and AAP job templates.

## Modules

| Module | Category | Description |
|---|---|---|
| [rgctl_install](modules/rgctl_install.md) | Setup | Install rgctl binary on local machines |
| [rgctl_discover](modules/rgctl_discover.md) | Lifecycle | Index a codebase |
| [rgctl_find](modules/rgctl_find.md) | Query | Search symbols by name, type, or language |
| [rgctl_callers](modules/rgctl_callers.md) | Query | Get incoming callers of a symbol |
| [rgctl_callees](modules/rgctl_callees.md) | Query | Get outgoing callees of a symbol |
| [rgctl_relations](modules/rgctl_relations.md) | Query | Traverse typed edges (extends, implements, …) |
| [rgctl_blast_radius](modules/rgctl_blast_radius.md) | Analysis | Compute impact zone for a symbol |
| [rgctl_clones](modules/rgctl_clones.md) | Analysis | Detect duplicate function implementations |
| [rgctl_metrics](modules/rgctl_metrics.md) | Analysis | PageRank, communities, betweenness |
| [rgctl_security](modules/rgctl_security.md) | Security | OSV advisory checks and taint analysis |
| [rgctl_report](modules/rgctl_report.md) | Output | Write JSON, Markdown, or HTML reports |

## Roles

| Role | Description |
|---|---|
| [analyze_pipeline](roles/analyze_pipeline.md) | Full pipeline: clone → index → scan → metrics → report |

## Quick Start

### Local machine (developer)

```bash
# Install rgctl
ansible-playbook rgctl.rgctl.install

# Analyze a Java repo for Spring4Shell
ansible-playbook my_analysis.yml
```

```yaml
# my_analysis.yml
- hosts: localhost
  roles:
    - role: rgctl.rgctl.analyze_pipeline
      vars:
        rgctl_git_url: "https://github.com/my-org/my-app"
        rgctl_dest: /tmp/analysis/my-app
        rgctl_checks: [deps_check, vuln_analyze]
        rgctl_osv_file: /path/to/advisory.json
        rgctl_report_format: html
        rgctl_report_dest: /tmp/analysis/report.html
```

### AAP (Ansible Automation Platform)

Build the included Execution Environment — it bakes rgctl into the image so no runtime download is needed:

```bash
cd execution-environment/
ansible-builder build -t rgctl-ee:0.4.26 -f execution-environment.yml
# Push and configure in AAP Controller
```

Then use `rgctl_manage_install: false` (the default) in your job templates.

## Installation

```bash
ansible-galaxy collection install rgctl.rgctl
```

Or from source:

```bash
ansible-galaxy collection install /path/to/rgctl-ansible-collection
```

## Requirements

- ansible-core >= 2.15
- rgctl v0.4.26+ on the target node (or baked into the EE)
- Python 3.9+ on the target node
