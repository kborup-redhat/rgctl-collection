#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_clones
short_description: Detect duplicate function implementations in a codebase
description:
  - Finds clone groups (duplicate functions) using exact, bloom (LSH), or
    fragment (structural) matching.
  - exact  — Type-1: identical code_hash groups
  - bloom  — Type-2: token-level Jaccard LSH candidates
  - fragment — Type-3/4: sub-function SESE hammock clones
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  mode:
    description: Clone detection mode.
    type: str
    choices: [exact, bloom, fragment]
    default: exact
  symbol:
    description: Optional symbol — report only the clone group containing it.
    type: str
    default: null
  min_loc:
    description: Minimum function lines of code to include.
    type: int
    default: 5
  exclude:
    description: Path globs to exclude (e.g. test, generated).
    type: list
    elements: str
    default: []
  lang:
    description: Language filter.
    type: str
    default: null
  threshold:
    description: Bloom min Jaccard threshold [0,1] (bloom mode only).
    type: float
    default: 0.85
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
rgctl_clones:
  description: List of clone groups, each with members and confidence.
  type: list
group_count:
  description: Total number of clone groups found.
  type: int
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import run_rgctl, parse_json, check_error_envelope


def run_module(module):
    p = module.params
    args = ["clones", "--mode", p["mode"], "--min-loc", str(p["min_loc"]),
            "--no-write"]
    if p["symbol"]:
        args.append(p["symbol"])
    if p["lang"]:
        args += ["--lang", p["lang"]]
    if p["mode"] == "bloom":
        args += ["--threshold", str(p["threshold"])]
    for excl in (p["exclude"] or []):
        args += ["--exclude", excl]

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "clones") or {}
        check_error_envelope(data, "clones")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    groups = data.get("groups", [])
    count = data.get("group_count", len(groups))
    module.exit_json(
        changed=False,
        rgctl_clones=groups,
        group_count=count,
        msg=f"{count} clone group(s) found (mode: {p['mode']})",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            mode=dict(type="str", choices=["exact", "bloom", "fragment"], default="exact"),
            symbol=dict(type="str", default=None),
            min_loc=dict(type="int", default=5),
            exclude=dict(type="list", elements="str", default=[]),
            lang=dict(type="str", default=None),
            threshold=dict(type="float", default=0.85),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=180),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
