#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_security
short_description: Run targeted security analysis with rgctl
description:
  - Runs rgctl security commands against an indexed codebase.
  - OSV-based checks (vuln_analyze, deps_check) require an OSV advisory JSON
    file obtained from https://osv.dev or a local advisory store.
  - Taint analysis requires a list of sink symbols and that discover was run
    with with_cfg=true (see rgctl_discover).
  - Always returns changed=false — analysis is read-only.
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  osv_file:
    description: >
      Path to an OSV advisory JSON file. Required for vuln_analyze and
      deps_check. Download from https://api.osv.dev/v1/vulns/<ID>.
    type: str
    default: ""
  checks:
    description: >
      Which checks to run. vuln_analyze and deps_check require osv_file.
      taint requires sink_symbols and discover run with with_cfg=true.
    type: list
    elements: str
    choices: [vuln_analyze, deps_check, taint]
    default: []
  sink_symbols:
    description: >
      List of sink symbols for taint analysis (e.g. ObjectMapper.readValue).
      Required when taint is in checks.
    type: list
    elements: str
    default: []
  taint_depth:
    description: Max call/data-flow depth for taint analysis.
    type: int
    default: 8
  severity_threshold:
    description: Minimum severity for above_threshold_count.
    type: str
    choices: [low, medium, high, critical]
    default: medium
  rgctl_bin:
    description: Path to the rgctl binary.
    type: str
    default: rgctl
  timeout:
    description: Timeout in seconds for each check.
    type: int
    default: 300
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
skipped_checks:
  description: Checks skipped due to missing prerequisites (osv_file, sink_symbols).
  type: list
"""

import json
import os
import subprocess

from ansible.module_utils.basic import AnsibleModule

SEVERITY_ORDER = ["low", "medium", "high", "critical"]


def _numeric_to_severity(numeric):
    if numeric >= 9:
        return "critical"
    if numeric >= 7:
        return "high"
    if numeric >= 4:
        return "medium"
    return "low"


def _normalize_severity(value):
    if isinstance(value, (int, float)):
        return _numeric_to_severity(value)
    lowered = str(value).lower().strip()
    aliases = {"none": "low", "info": "low", "informational": "low",
               "moderate": "medium", "warning": "medium"}
    return aliases.get(lowered, lowered if lowered in SEVERITY_ORDER else "low")


def _normalize_finding(finding, check_name):
    finding = dict(finding)
    finding.setdefault("check", check_name)
    finding["severity"] = _normalize_severity(finding.get("severity", "low"))
    return finding


def _run_cmd(cmd, path, rgctl_bin, timeout):
    full_cmd = [rgctl_bin, "-r", path, "-f", "json"] + cmd
    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "rgctl not found in PATH. For AAP, build and deploy the "
            "execution-environment image. For local machines, use "
            "rgctl.rgctl.rgctl_install first."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"rgctl {' '.join(cmd)} timed out after {timeout}s")
    return result


def _parse_findings(result, check_name):
    stdout = result.stdout.strip()
    if result.returncode != 0:
        try:
            data = json.loads(stdout) if stdout else None
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list) and data:
            return [_normalize_finding(f, check_name) for f in data]
        raise RuntimeError(
            f"rgctl {check_name} failed (exit {result.returncode}): "
            f"{result.stderr.strip() or stdout or 'no output'}"
        )
    if not stdout:
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [_normalize_finding(f, check_name) for f in data]
    if isinstance(data, dict):
        if "findings" in data and isinstance(data["findings"], list):
            return [_normalize_finding(f, check_name) for f in data["findings"]]
        if any(k in data for k in ("message", "severity", "location", "variable",
                                    "exploitability", "verdict")):
            return [_normalize_finding(data, check_name)]
    return []


def _run_vuln_analyze(path, osv_file, rgctl_bin, timeout):
    result = _run_cmd(["vuln", "analyze", "--osv", osv_file], path, rgctl_bin, timeout)
    return _parse_findings(result, "vuln_analyze")


def _run_deps_check(path, osv_file, rgctl_bin, timeout):
    result = _run_cmd(["deps", "check", "--osv", osv_file], path, rgctl_bin, timeout)
    return _parse_findings(result, "deps_check")


def _run_taint(path, sink_symbol, depth, rgctl_bin, timeout):
    result = _run_cmd(
        ["taint", "--sink", sink_symbol, "--source", "external", "--depth", str(depth)],
        path, rgctl_bin, timeout,
    )
    return _parse_findings(result, "taint")


def _above_threshold(findings, threshold):
    threshold_idx = SEVERITY_ORDER.index(threshold)
    return sum(
        1 for f in findings
        if SEVERITY_ORDER.index(f.get("severity", "low")) >= threshold_idx
    )


def run_module(module):
    path = module.params["path"]
    osv_file = module.params["osv_file"]
    checks = module.params["checks"]
    sink_symbols = module.params["sink_symbols"]
    taint_depth = module.params["taint_depth"]
    severity_threshold = module.params["severity_threshold"]
    rgctl_bin = module.params["rgctl_bin"]
    timeout = module.params["timeout"]

    all_findings = []
    skipped = []

    try:
        for check in checks:
            if check in ("vuln_analyze", "deps_check"):
                if not osv_file:
                    skipped.append(f"{check} (osv_file not provided)")
                    continue
                if not os.path.exists(osv_file):
                    module.fail_json(msg=f"osv_file not found: {osv_file}")
                if check == "vuln_analyze":
                    all_findings.extend(_run_vuln_analyze(path, osv_file, rgctl_bin, timeout))
                else:
                    all_findings.extend(_run_deps_check(path, osv_file, rgctl_bin, timeout))

            elif check == "taint":
                if not sink_symbols:
                    skipped.append("taint (sink_symbols not provided)")
                    continue
                for symbol in sink_symbols:
                    all_findings.extend(_run_taint(path, symbol, taint_depth, rgctl_bin, timeout))

    except RuntimeError as e:
        module.fail_json(msg=str(e))

    count = _above_threshold(all_findings, severity_threshold)

    module.exit_json(
        changed=False,
        rgctl_security_findings=all_findings,
        above_threshold_count=count,
        skipped_checks=skipped,
        msg=f"{len(all_findings)} findings ({count} at or above {severity_threshold})"
              + (f"; skipped: {', '.join(skipped)}" if skipped else ""),
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            osv_file=dict(type="str", default=""),
            checks=dict(
                type="list",
                elements="str",
                default=[],
            ),
            sink_symbols=dict(type="list", elements="str", default=[]),
            taint_depth=dict(type="int", default=8),
            severity_threshold=dict(
                type="str",
                choices=["low", "medium", "high", "critical"],
                default="medium",
            ),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=300),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
