#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_blast_radius
short_description: Compute the blast radius (impact zone) for a symbol
description:
  - Returns the transitive upstream impact zone for a function symbol.
  - Answers "what breaks if I change this?"
  - Requires a function symbol — disambiguate with class_name, file, or line
    if the name is not unique.
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  symbol:
    description: Function symbol name, UUID, or FQN.
    type: str
    required: true
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
  depth:
    description: Limit traversal to N incoming call hops. Default is full transitive closure.
    type: int
    default: null
  summary:
    description: Return compact summary instead of full topology.
    type: bool
    default: false
  classify_boundary:
    description: Label impact nodes with boundary types (REST, messaging, …).
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
rgctl_blast_radius:
  description: Full blast radius result (target, metrics, topology, gatekeeping).
  type: dict
impact_score:
  description: Numeric blast radius score from rgctl metrics.
  type: float
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import run_rgctl, parse_json, check_error_envelope


def run_module(module):
    p = module.params
    args = ["blast-radius", p["symbol"]]
    if p["class_name"]:
        args += ["--class", p["class_name"]]
    if p["file"]:
        args += ["--file", p["file"]]
    if p["line"] is not None:
        args += ["--line", str(p["line"])]
    if p["depth"] is not None:
        args += ["--depth", str(p["depth"])]
    if p["summary"]:
        args.append("--summary")
    if p["classify_boundary"]:
        args.append("--classify-boundary")

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "blast-radius")
        if data is None:
            module.fail_json(msg="rgctl blast-radius returned no output")
        check_error_envelope(data, "blast-radius")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    score = (data.get("metrics") or {}).get("score", 0.0)
    module.exit_json(
        changed=False,
        rgctl_blast_radius=data,
        impact_score=score,
        msg=f"Blast radius score: {score:.2f}, impact zone: {(data.get('metrics') or {}).get('impact_zone_size', 0)} symbols",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            symbol=dict(type="str", required=True),
            class_name=dict(type="str", default=None),
            file=dict(type="str", default=None),
            line=dict(type="int", default=None),
            depth=dict(type="int", default=None),
            summary=dict(type="bool", default=False),
            classify_boundary=dict(type="bool", default=False),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=120),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
