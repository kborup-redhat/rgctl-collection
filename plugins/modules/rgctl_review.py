#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_review
short_description: PR call-path analysis comparing two graph snapshots
description:
  - Runs `rgctl review paths` to compare a base and head graph snapshot,
    returning the call-path diff for a pull request.
  - Each snapshot is a directory containing `graph.snapshot.bin`, typically
    produced by running `rgctl discover` on the base and head branches.
options:
  path:
    description: Absolute path to the codebase root.
    type: str
    required: true
  base_snapshot:
    description: Path to the base snapshot directory (contains graph.snapshot.bin).
    type: str
    required: true
  head_snapshot:
    description: Path to the head snapshot directory (contains graph.snapshot.bin).
    type: str
    required: true
  rgctl_bin:
    description: Path to the rgctl binary.
    type: str
    default: rgctl
  timeout:
    description: Timeout in seconds.
    type: int
    default: 180
"""
RETURN = r"""
changed:
  type: bool
rgctl_review_paths:
  description: Parsed JSON result from rgctl review paths.
  type: dict
added_paths:
  description: Number of new call paths introduced.
  type: int
removed_paths:
  description: Number of call paths removed.
  type: int
msg:
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import run_rgctl, parse_json, check_error_envelope


def run_module(module):
    p = module.params
    args = [
        "review", "paths",
        "--base", p["base_snapshot"],
        "--head", p["head_snapshot"],
    ]

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "review paths") or {}
        check_error_envelope(data, "review paths")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    added = len(data.get("added", []))
    removed = len(data.get("removed", []))

    module.exit_json(
        changed=False,
        rgctl_review_paths=data,
        added_paths=added,
        removed_paths=removed,
        msg=f"PR review: +{added} call path(s), -{removed} call path(s)",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            base_snapshot=dict(type="str", required=True),
            head_snapshot=dict(type="str", required=True),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=180),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
