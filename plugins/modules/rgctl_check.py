#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_check
short_description: Run the rgctl CI policy gateway against an indexed codebase
description:
  - Evaluates a policy file against the graph index and returns violations.
  - Does NOT fail the module on policy violations — returns passed=false so
    the playbook can decide how to respond.
  - Fails only on hard errors (binary missing, timeout, bad JSON).
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  policy_file:
    description: Path to the policy YAML/JSON file.
    type: str
    required: true
  base_ref:
    description: Base git ref for temporal checks.
    type: str
    default: null
  head_ref:
    description: Head git ref for temporal checks.
    type: str
    default: null
  strict:
    description: Treat warnings as failures.
    type: bool
    default: false
  rgctl_bin:
    description: Path to the rgctl binary.
    type: str
    default: rgctl
  timeout:
    description: Timeout in seconds.
    type: int
    default: 120
"""
RETURN = r"""
changed:
  type: bool
rgctl_check_result:
  description: Parsed JSON result from rgctl check.
  type: dict
passed:
  description: True when no violations were found.
  type: bool
violation_count:
  description: Number of policy violations.
  type: int
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import run_rgctl, parse_json


def run_module(module):
    p = module.params
    args = ["check", "--policy-file", p["policy_file"]]
    if p["base_ref"]:
        args += ["--base-ref", p["base_ref"]]
    if p["head_ref"]:
        args += ["--head-ref", p["head_ref"]]
    if p["strict"]:
        args.append("--strict")

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        # check can return non-zero when violations found — parse stdout regardless
        data = parse_json(stdout, "check") or {}
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    violations = data.get("violations", [])
    violation_count = len(violations)
    passed = violation_count == 0

    module.exit_json(
        changed=False,
        rgctl_check_result=data,
        passed=passed,
        violation_count=violation_count,
        msg=f"Policy check {'passed' if passed else 'failed'}: {violation_count} violation(s)",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            policy_file=dict(type="str", required=True),
            base_ref=dict(type="str", default=None),
            head_ref=dict(type="str", default=None),
            strict=dict(type="bool", default=False),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=120),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
