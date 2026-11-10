#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_callers
short_description: Get incoming callers of a symbol
description:
  - Returns all symbols that call the given symbol, up to the specified depth.
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  symbol:
    description: Symbol name, UUID, or FQN.
    type: str
    required: true
  depth:
    description: Call depth to traverse.
    type: int
    default: 1
  class_name:
    description: Class/namespace filter to disambiguate overloads.
    type: str
    default: null
  file:
    description: Source file path filter.
    type: str
    default: null
  line:
    description: Definition line to disambiguate overloads.
    type: int
    default: null
  limit:
    description: Maximum results.
    type: int
    default: 50
  rgctl_bin:
    description: Path to the rgctl binary.
    type: str
    default: rgctl
  timeout:
    description: Timeout in seconds.
    type: int
    default: 60
"""
RETURN = r"""
changed:
  type: bool
rgctl_callers:
  description: List of symbols that call the given symbol.
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import run_rgctl, parse_json, check_error_envelope


def run_module(module):
    p = module.params
    args = ["callers", p["symbol"], "--depth", str(p["depth"]),
            "--limit", str(p["limit"])]
    if p["class_name"]:
        args += ["--class", p["class_name"]]
    if p["file"]:
        args += ["--file", p["file"]]
    if p["line"] is not None:
        args += ["--line", str(p["line"])]

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "callers") or {}
        check_error_envelope(data, "callers")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    callers = data.get("callers", [])
    module.exit_json(
        changed=False,
        rgctl_callers=callers,
        total=len(callers),
        msg=f"{len(callers)} caller(s) found",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            symbol=dict(type="str", required=True),
            depth=dict(type="int", default=1),
            class_name=dict(type="str", default=None),
            file=dict(type="str", default=None),
            line=dict(type="int", default=None),
            limit=dict(type="int", default=50),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=60),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
