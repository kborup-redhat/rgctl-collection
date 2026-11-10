#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_inventory
short_description: Aggregate symbol and edge counts from an indexed codebase
description:
  - Returns counts of symbols or edges grouped by a chosen dimension (type, lang, edge, file, …).
  - Useful for understanding the shape of a codebase at a glance.
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  by:
    description: Aggregation dimension.
    type: str
    choices: [type, edge, lang, file, community, import-prefix]
    default: type
  limit:
    description: Maximum number of buckets to return.
    type: int
    default: 50
  prefix:
    description: Filter bucket keys by this prefix (e.g. javax. for Java imports).
    type: str
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
rgctl_inventory:
  description: List of {key, count} dicts.
  type: list
by:
  description: The aggregation dimension used.
  type: str
total_symbols:
  description: Sum of all counts across all buckets.
  type: int
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import run_rgctl, parse_json, check_error_envelope


def run_module(module):
    p = module.params
    args = ["inventory", "--by", p["by"], "--limit", str(p["limit"])]
    if p["prefix"]:
        args += ["--prefix", p["prefix"]]

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "inventory") or {}
        check_error_envelope(data, "inventory")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    counts = data.get("counts", [])
    total = sum(c.get("count", 0) for c in counts)

    module.exit_json(
        changed=False,
        rgctl_inventory=counts,
        by=data.get("by", p["by"]),
        total_symbols=total,
        msg=f"{len(counts)} bucket(s) by {p['by']}, total={total}",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            by=dict(
                type="str",
                choices=["type", "edge", "lang", "file", "community", "import-prefix"],
                default="type",
            ),
            limit=dict(type="int", default=50),
            prefix=dict(type="str", default=None),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=60),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
