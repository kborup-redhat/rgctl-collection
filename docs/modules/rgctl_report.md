# rgctl.rgctl.rgctl_report

Write analysis results to a JSON, Markdown, or HTML report file.

## Synopsis

Serializes security findings, index metadata, and optional metrics into a report file. Idempotent: compares a SHA256 hash of the new content against the existing file and only writes when the content has changed. Use this as the final step of an analysis pipeline to produce a human-readable or machine-parseable artifact.

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `dest` | str | yes | — | Destination file path for the report |
| `findings` | list | yes | — | Security findings list from `rgctl_security` (`rgctl_security_findings`) |
| `format` | str | no | `json` | Output format: `json`, `markdown`, or `html` |
| `index_info` | dict | no | `{}` | Index summary dict from `rgctl_discover` (`rgctl_index`) |
| `metrics` | dict | no | `{}` | Metrics dict from `rgctl_metrics` (`rgctl_metrics`) |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | `true` if the file was written or updated, `false` if content was identical |
| `report_path` | str | Absolute path to the written report |

## Notes

**Format comparison:**

| Format | Best for | Contents |
|---|---|---|
| `json` | Downstream automation, dashboards, further processing | Structured `{"index": …, "findings": […], "metrics": …}` |
| `markdown` | GitHub/GitLab PR comments, wikis, Confluence | GFM tables for findings and PageRank; community structure summary |
| `html` | Human review, email, AAP job artifacts | Styled single-page report with coloured severity badges and hover rows |

**Idempotency:** The file is only written when the SHA256 of the new content differs from the existing file. Running the pipeline twice on an unchanged codebase produces `changed: false` on the second run.

**Severity badge colours in HTML:** `critical` → red, `high` → orange, `medium` → yellow, `low` → green.

**Metrics in report:** When `metrics` is provided, `markdown` and `html` formats include a Code Metrics section with the top-N PageRank table and community structure summary.

## Examples

```yaml
# JSON report (default) — machine-readable
- name: Write JSON report
  rgctl.rgctl.rgctl_report:
    dest: /tmp/analysis/report.json
    findings: "{{ security.rgctl_security_findings }}"
    index_info: "{{ discover.rgctl_index }}"
    metrics: "{{ metrics.rgctl_metrics }}"
  register: report

# HTML report — human-readable with styling
- name: Write HTML report
  rgctl.rgctl.rgctl_report:
    dest: /tmp/analysis/report.html
    format: html
    findings: "{{ security.rgctl_security_findings }}"
    index_info: "{{ discover.rgctl_index }}"
    metrics: "{{ metrics.rgctl_metrics }}"

# Markdown report — suitable for a GitHub PR comment
- name: Write Markdown report
  rgctl.rgctl.rgctl_report:
    dest: "{{ workspace }}/rgctl-report.md"
    format: markdown
    findings: "{{ security.rgctl_security_findings }}"
    index_info: "{{ discover.rgctl_index }}"
  register: md_report

# Post Markdown report as a GitHub PR comment (example)
- name: Post report to PR
  ansible.builtin.command:
    cmd: >
      gh pr comment {{ pr_number }}
      --body-file {{ md_report.report_path }}
  when: md_report.changed
```
