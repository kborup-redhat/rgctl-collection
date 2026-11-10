#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_diff
short_description: Diff two rgctl graph snapshots
description:
  - Compares two graph snapshots (base vs head) and returns added, removed,
    and changed symbols.
  - Useful for PR review workflows to surface structural changes between branches.
  - Snapshots are directories containing graph.snapshot.bin, produced by
    rgctl discover or rgctl export.
options:
  path:
    description: Absolute path to the codebase root.
    type: str
    required: true
  base_snapshot:
    description: Path to the base snapshot directory (e.g. main branch).
    type: str
    required: true
  head_snapshot:
    description: Path to the head snapshot directory (e.g. feature branch).
    type: str
    required: true
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
  description: Always false — diff is read-only.
  type: bool
rgctl_diff:
  description: Full diff result with added, removed, changed lists and stats.
  type: dict
added_count:
  description: Number of added symbols.
  type: int
removed_count:
  description: Number of removed symbols.
  type: int
changed_count:
  description: Number of changed symbols.
  type: int
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import (
    run_rgctl, parse_json, check_error_envelope
)


def run_module(module):
    p = module.params
    args = ["diff", "--base", p["base_snapshot"], "--head", p["head_snapshot"]]

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "diff") or {}
        check_error_envelope(data, "diff")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    stats = data.get("stats", {})
    module.exit_json(
        changed=False,
        rgctl_diff=data,
        added_count=stats.get("added", len(data.get("added", []))),
        removed_count=stats.get("removed", len(data.get("removed", []))),
        changed_count=stats.get("changed", len(data.get("changed", []))),
        msg=(f"Diff: +{stats.get('added', 0)} added, "
             f"-{stats.get('removed', 0)} removed, "
             f"~{stats.get('changed', 0)} changed"),
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            base_snapshot=dict(type="str", required=True),
            head_snapshot=dict(type="str", required=True),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=120),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
