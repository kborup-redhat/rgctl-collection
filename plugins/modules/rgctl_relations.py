#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_relations
short_description: Traverse typed edges in the code graph
description:
  - Returns edges of a specific type (calls, uses, extends, implements,
    overrides, cochangeswith, annotatedwith, exposesroute, injects, …)
    from/to a symbol.
  - Omit symbol for a seedless scan over all edges of that type.
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  edge:
    description: Edge type to traverse (calls, uses, extends, implements, …).
    type: str
    required: true
  symbol:
    description: Seed symbol (omit for seedless typed-edge scan).
    type: str
    default: null
  direction:
    description: Traversal direction.
    type: str
    choices: [in, out, both]
    default: out
  depth:
    description: Traversal depth.
    type: int
    default: 1
  limit:
    description: Maximum results.
    type: int
    default: 50
  class_name:
    description: Class/namespace filter.
    type: str
    default: null
  file:
    description: Source file filter.
    type: str
    default: null
  line:
    description: Definition line disambiguator.
    type: int
    default: null
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
rgctl_relations:
  description: List of edges matching the query.
  type: list
total:
  description: Total edge count.
  type: int
target:
  description: Resolved target symbol (when symbol is provided).
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import run_rgctl, parse_json, check_error_envelope


def run_module(module):
    p = module.params
    args = ["relations", "--edge", p["edge"], "--direction", p["direction"],
            "--depth", str(p["depth"]), "--limit", str(p["limit"])]
    if p["symbol"]:
        args.append(p["symbol"])
    if p["class_name"]:
        args += ["--class", p["class_name"]]
    if p["file"]:
        args += ["--file", p["file"]]
    if p["line"] is not None:
        args += ["--line", str(p["line"])]

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "relations") or {}
        check_error_envelope(data, "relations")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    edges = data.get("edges", [])
    module.exit_json(
        changed=False,
        rgctl_relations=edges,
        total=data.get("total", len(edges)),
        target=data.get("target", {}),
        msg=f"{len(edges)} {p['edge']} edge(s) found",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            edge=dict(type="str", required=True),
            symbol=dict(type="str", default=None),
            direction=dict(type="str", choices=["in", "out", "both"], default="out"),
            depth=dict(type="int", default=1),
            limit=dict(type="int", default=50),
            class_name=dict(type="str", default=None),
            file=dict(type="str", default=None),
            line=dict(type="int", default=None),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=60),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
