# rgctl.rgctl Ansible Collection

Ansible collection for automating code analysis with [rgctl](https://github.com/rgctl/rgctl).

## Modules

- `rgctl.rgctl.rgctl_install` — Install rgctl binary on local machines
- `rgctl.rgctl.rgctl_discover` — Index a codebase with rgctl
- `rgctl.rgctl.rgctl_security` — Run security scans (vuln, deps, taint)
- `rgctl.rgctl.rgctl_report` — Write analysis reports

## Roles

- `rgctl.rgctl.analyze_pipeline` — Full pipeline: clone → index → scan → report

## Quick Start (local machine)

```bash
ansible-playbook rgctl.rgctl.install
ansible-playbook your_analysis.yml
```

## AAP Usage

Build the execution environment first:

```bash
cd execution-environment/
ansible-builder build -t rgctl-ee:latest
```

Then use the EE in your AAP job template.
