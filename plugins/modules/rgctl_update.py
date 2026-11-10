#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_update
short_description: Incrementally update the rgctl graph index
description:
  - Patches the graph index for changed files only. Faster than a full discover.
  - Returns changed=true when files were actually re-indexed.
options:
  path:
    description: Absolute path to the codebase root.
    type: str
    required: true
  files:
    description: Specific repo-relative file paths to update. Empty means all changed files.
    type: list
    elements: str
    default: []
  rgctl_bin:
    description: Path to the rgctl binary.
    type: str
    default: rgctl
  timeout:
    description: Timeout in seconds.
    type: int
    default: 300
"""
RETURN = r"""
changed:
  description: True when at least one file was re-indexed.
  type: bool
rgctl_update:
  description: Raw parsed JSON result from rgctl update.
  type: dict
msg:
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import run_rgctl, parse_json, check_error_envelope


def run_module(module):
    p = module.params
    args = ["update", p["path"]]
    if p["files"]:
        args += ["--files", ",".join(p["files"])]

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "update") or {}
        check_error_envelope(data, "update")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    metrics = data.get("metrics", {})
    files_indexed = metrics.get("files_indexed", 0)
    changed = files_indexed > 0

    module.exit_json(
        changed=changed,
        rgctl_update=data,
        msg=f"{files_indexed} file(s) re-indexed",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            files=dict(type="list", elements="str", default=[]),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=300),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
