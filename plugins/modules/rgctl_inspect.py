#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_inspect
short_description: Inspect the CFG, PDG, or dominator tree of a function
description:
  - Fetches the control-flow graph (cfg), program dependence graph (pdg),
    or dominator tree (dom) for a function symbol.
  - Requires the codebase to have been indexed with discover --with-cfg.
  - If cfg artifacts are not present, the module fails with guidance to
    re-run rgctl_discover with with_cfg=true.
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  symbol:
    description: Function symbol name.
    type: str
    required: true
  subcommand:
    description: Which graph structure to retrieve.
    type: str
    choices: [cfg, pdg, dom]
    default: cfg
  class_name:
    description: Class/namespace filter to disambiguate overloads.
    type: str
    default: null
  file:
    description: Source file path filter.
    type: str
    default: null
  line:
    description: Definition line to disambiguate.
    type: int
    default: null
  prune:
    description: Remove unreachable blocks before returning.
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
rgctl_inspect:
  description: Parsed graph structure (blocks, edges, metadata).
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import (
    run_rgctl, parse_json, check_error_envelope
)

CFG_MISSING_HINT = (
    "CFG artifacts not found. Re-run rgctl_discover with with_cfg=true "
    "to build the CFG/PDG index, then retry."
)


def run_module(module):
    p = module.params
    args = ["inspect", p["symbol"], p["subcommand"]]
    if p["class_name"]:
        args += ["--class", p["class_name"]]
    if p["file"]:
        args += ["--file", p["file"]]
    if p["line"] is not None:
        args += ["--line", str(p["line"])]
    if p["prune"]:
        args.append("--prune")

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, f"inspect {p['subcommand']}") or {}
        # CFG not built → rgctl returns a specific error
        if isinstance(data, dict) and "cfg" in str(data.get("error_code", "")).lower():
            module.fail_json(msg=CFG_MISSING_HINT)
        if isinstance(data, dict) and not data and rc != 0:
            # Empty JSON + non-zero likely means CFG artifacts missing
            stderr_lower = stderr.lower()
            if "cfg" in stderr_lower or "not found" in stderr_lower:
                module.fail_json(msg=CFG_MISSING_HINT)
        check_error_envelope(data, f"inspect {p['subcommand']}")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    module.exit_json(
        changed=False,
        rgctl_inspect=data,
        msg=f"inspect {p['subcommand']} for '{p['symbol']}' complete",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            symbol=dict(type="str", required=True),
            subcommand=dict(type="str", choices=["cfg", "pdg", "dom"], default="cfg"),
            class_name=dict(type="str", default=None),
            file=dict(type="str", default=None),
            line=dict(type="int", default=None),
            prune=dict(type="bool", default=False),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=120),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
