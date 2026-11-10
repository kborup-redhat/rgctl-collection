#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_report
short_description: Write rgctl analysis results to a file
description:
  - Writes security findings and index info to a JSON or Markdown report file.
  - Idempotent - only writes when content has changed (SHA256 comparison).
options:
  dest:
    description: Destination file path for the report.
    type: str
    required: true
  findings:
    description: List of security findings from rgctl_security.
    type: list
    required: true
  format:
    description: Output format.
    type: str
    choices: [json, markdown]
    default: json
  index_info:
    description: Index summary dict from rgctl_discover.
    type: dict
    default: {}
  metrics:
    description: Metrics dict from rgctl_metrics (optional).
    type: dict
    default: {}
"""

RETURN = r"""
changed:
  description: Whether the report file was written or updated.
  type: bool
report_path:
  description: Path to the written report.
  type: str
"""

import hashlib
import json
import os

from ansible.module_utils.basic import AnsibleModule


def _build_json_content(index_info, findings, metrics):
    return json.dumps({"index": index_info, "findings": findings, "metrics": metrics}, indent=2)


def _build_markdown_content(index_info, findings, metrics):
    lines = ["# rgctl Security Report", ""]
    if index_info:
        lines += [
            "## Index Summary",
            "",
            "| Field | Value |",
            "|---|---|",
        ]
        for k, v in index_info.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")

    lines += [
        "## Security Findings",
        "",
        f"Total findings: {len(findings)}",
        "",
    ]

    if findings:
        lines += [
            "| Check | Severity | Message | Location |",
            "|---|---|---|---|",
        ]
        for f in findings:
            check = f.get("check", "")
            sev = f.get("severity", "")
            msg = f.get("message", "")
            loc = f.get("location", "")
            lines.append(f"| {check} | {sev} | {msg} | {loc} |")
    else:
        lines.append("No findings.")

    if metrics:
        lines += ["", "## Code Metrics", ""]
        if "pagerank_top" in metrics:
            lines += [
                "### Top Symbols by PageRank (highest coupling/impact)",
                "",
                "| Symbol | Kind | File | Score |",
                "|---|---|---|---|",
            ]
            for s in metrics["pagerank_top"][:10]:
                name = s.get("qualified_name", s.get("name", ""))
                kind = s.get("kind", "")
                fpath = s.get("file_path", "")
                score = f"{s.get('pagerank', 0):.6f}"
                lines.append(f"| {name} | {kind} | {fpath} | {score} |")
            lines.append("")
        if "communities" in metrics:
            c = metrics["communities"]
            lines += [
                "### Community Structure",
                "",
                f"- Communities detected: {c.get('count', 0)}",
                f"- Modularity: {c.get('modularity', 0):.4f}",
                f"- Symbols assigned: {c.get('assignments', 0)}",
                "",
            ]

    return "\n".join(lines) + "\n"


def _sha256(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def run_module(module):
    dest = module.params["dest"]
    findings = module.params["findings"]
    fmt = module.params["format"]
    index_info = module.params["index_info"] or {}
    metrics = module.params["metrics"] or {}

    if fmt == "json":
        new_content = _build_json_content(index_info, findings, metrics)
    else:
        new_content = _build_markdown_content(index_info, findings, metrics)

    new_hash = _sha256(new_content)

    if os.path.exists(dest):
        try:
            with open(dest) as f:
                existing = f.read()
            if _sha256(existing) == new_hash:
                module.exit_json(changed=False, report_path=dest, msg="Report unchanged")
        except OSError:
            pass

    try:
        with open(dest, "w") as f:
            f.write(new_content)
    except OSError as e:
        module.fail_json(msg=f"Could not write report to {dest}: {e}")

    module.exit_json(changed=True, report_path=dest, msg=f"Report written to {dest}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            dest=dict(type="str", required=True),
            findings=dict(type="list", required=True),
            format=dict(type="str", choices=["json", "markdown"], default="json"),
            index_info=dict(type="dict", default={}),
            metrics=dict(type="dict", default={}),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
