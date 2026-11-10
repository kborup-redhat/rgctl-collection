#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_security
short_description: Run security scans with rgctl
description:
  - Runs rgctl security command group (vuln, deps, security, taint) against
    an indexed codebase.
  - Always returns changed=false — analysis is read-only.
  - Taint findings are read from .rgctl/dashboard/taint/ after the scan.
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  checks:
    description: Which security checks to run.
    type: list
    elements: str
    default: [vuln, deps, security, taint]
  severity_threshold:
    description: Minimum severity for above_threshold_count.
    type: str
    choices: [low, medium, high, critical]
    default: medium
  rgctl_bin:
    description: Path to the rgctl binary.
    type: str
    default: rgctl
"""

RETURN = r"""
changed:
  description: Always false — analysis does not mutate state.
  type: bool
rgctl_security_findings:
  description: All findings from the requested checks.
  type: list
above_threshold_count:
  description: Number of findings at or above severity_threshold.
  type: int
"""

import json
import os
import subprocess

from ansible.module_utils.basic import AnsibleModule

SEVERITY_ORDER = ["low", "medium", "high", "critical"]

# Numeric severity (0-10) to string mapping
def _numeric_to_severity(numeric):
    if numeric >= 9:
        return "critical"
    if numeric >= 7:
        return "high"
    if numeric >= 4:
        return "medium"
    return "low"


def _normalize_finding(finding, check_name):
    finding = dict(finding)
    finding.setdefault("check", check_name)
    # Normalize numeric severity fields to string
    if "severity" in finding and isinstance(finding["severity"], (int, float)):
        finding["severity"] = _numeric_to_severity(finding["severity"])
    finding.setdefault("severity", "low")
    return finding


def _run_check(check, path, rgctl_bin):
    try:
        result = subprocess.run(
            [rgctl_bin, check, "-f", "json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=path,
        )
    except FileNotFoundError:
        raise RuntimeError(
            f"rgctl not found in PATH. For AAP, build and deploy the "
            f"execution-environment image. For local machines, use "
            f"rgctl.rgctl.rgctl_install first."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"rgctl {check} timed out after 120s")

    if result.returncode != 0:
        # Non-zero exit may still yield valid JSON findings on stdout
        pass

    stdout = result.stdout.strip()
    if not stdout:
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return []

    if isinstance(data, list):
        return [_normalize_finding(f, check) for f in data]
    if isinstance(data, dict):
        # Some commands return a single finding object
        return [_normalize_finding(data, check)]
    return []


def _read_taint_dashboard(path):
    taint_dir = os.path.join(path, ".rgctl", "dashboard", "taint")
    findings = []
    if not os.path.isdir(taint_dir):
        return findings
    for fname in os.listdir(taint_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(taint_dir, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    findings.append(_normalize_finding(item, "taint"))
            elif isinstance(data, dict):
                findings.append(_normalize_finding(data, "taint"))
        except (json.JSONDecodeError, OSError):
            continue
    return findings


def _above_threshold(findings, threshold):
    threshold_idx = SEVERITY_ORDER.index(threshold)
    return sum(
        1 for f in findings
        if SEVERITY_ORDER.index(f.get("severity", "low")) >= threshold_idx
    )


def run_module(module):
    path = module.params["path"]
    checks = module.params["checks"]
    severity_threshold = module.params["severity_threshold"]
    rgctl_bin = module.params["rgctl_bin"]

    all_findings = []

    try:
        for check in checks:
            if check == "taint":
                # Trigger taint analysis, then read dashboard files
                _run_check("taint", path, rgctl_bin)
                all_findings.extend(_read_taint_dashboard(path))
            else:
                all_findings.extend(_run_check(check, path, rgctl_bin))
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    count = _above_threshold(all_findings, severity_threshold)

    module.exit_json(
        changed=False,
        rgctl_security_findings=all_findings,
        above_threshold_count=count,
        msg=f"{len(all_findings)} findings ({count} at or above {severity_threshold})",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            checks=dict(type="list", elements="str", default=["vuln", "deps", "security", "taint"]),
            severity_threshold=dict(
                type="str",
                choices=["low", "medium", "high", "critical"],
                default="medium",
            ),
            rgctl_bin=dict(type="str", default="rgctl"),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
