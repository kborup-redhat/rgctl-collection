#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_slice
short_description: Compute a program slice for a variable at a source location
description:
  - Computes a backward or forward program slice — the set of statements that
    influence (backward) or are influenced by (forward) a variable at a given
    source line.
  - Builds and caches the CFG/PDG lazily for the enclosing function.
options:
  path:
    description: Absolute path to the codebase root.
    type: str
    required: true
  file:
    description: Source file path (relative to repo root or absolute).
    type: str
    required: true
  line:
    description: Line number of the slicing criterion.
    type: int
    required: true
  variable:
    description: Variable name at the slicing criterion.
    type: str
    required: true
  direction:
    description: Slice direction.
    type: str
    choices: [backward, forward]
    default: backward
  function:
    description: Enclosing function name (auto-resolved from file:line when omitted).
    type: str
    default: null
  taint:
    description: Run as taint trace instead of a pure data/control slice.
    type: bool
    default: false
  with_alias:
    description: Expand criterion via intra-procedural may-alias heuristics.
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
rgctl_slice:
  description: Full slice result including statement list and metadata.
  type: dict
slice_length:
  description: Number of statements in the slice.
  type: int
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import (
    run_rgctl, parse_json, check_error_envelope
)


def run_module(module):
    p = module.params
    args = ["slice", p["file"],
            "--line", str(p["line"]),
            "--variable", p["variable"],
            "--direction", p["direction"]]
    if p["function"]:
        args += ["--function", p["function"]]
    if p["taint"]:
        args.append("--taint")
    if p["with_alias"]:
        args.append("--with-alias")

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "slice") or {}
        check_error_envelope(data, "slice")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    slice_stmts = data.get("slice", [])
    module.exit_json(
        changed=False,
        rgctl_slice=data,
        slice_length=data.get("length", len(slice_stmts)),
        msg=f"Slice of '{p['variable']}' at {p['file']}:{p['line']} → {len(slice_stmts)} statement(s)",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            file=dict(type="str", required=True),
            line=dict(type="int", required=True),
            variable=dict(type="str", required=True),
            direction=dict(type="str", choices=["backward", "forward"], default="backward"),
            function=dict(type="str", default=None),
            taint=dict(type="bool", default=False),
            with_alias=dict(type="bool", default=False),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=120),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
