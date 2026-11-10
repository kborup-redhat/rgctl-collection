#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_find
short_description: Find symbols in an indexed codebase by name or type
description:
  - Searches the rgctl graph index for symbols matching a name pattern or type filter.
  - Supports glob patterns (e.g. User*, *Service*), exact match, and type/language filters.
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  pattern:
    description: Name or glob pattern to search (e.g. Owner, User*, *Service*).
    type: str
    default: ""
  symbol_type:
    description: Filter by node type (function, class, import, annotation, …).
    type: str
    default: null
  file_glob:
    description: Path glob filter.
    type: str
    default: null
  lang:
    description: Language filter (java, rust, python, …).
    type: str
    default: null
  scope:
    description: Qualified name prefix scope.
    type: str
    default: null
  limit:
    description: Maximum number of results.
    type: int
    default: 50
  exact:
    description: Exact name match (disable glob).
    type: bool
    default: false
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
rgctl_find_results:
  description: List of matching symbol entities.
  type: list
total:
  description: Total matches in the graph.
  type: int
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import run_rgctl, parse_json, check_error_envelope


def run_module(module):
    p = module.params
    args = ["find"]
    if p["pattern"]:
        args.append(p["pattern"])
    if p["symbol_type"]:
        args += ["-t", p["symbol_type"]]
    if p["file_glob"]:
        args += ["--file", p["file_glob"]]
    if p["lang"]:
        args += ["--lang", p["lang"]]
    if p["scope"]:
        args += ["--scope", p["scope"]]
    if p["exact"]:
        args.append("--exact")
    args += ["--limit", str(p["limit"])]

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "find") or {}
        check_error_envelope(data, "find")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    entities = data.get("entities", [])
    module.exit_json(
        changed=False,
        rgctl_find_results=entities,
        total=data.get("total", len(entities)),
        msg=f"Found {len(entities)} symbol(s)",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            pattern=dict(type="str", default=""),
            symbol_type=dict(type="str", default=None),
            file_glob=dict(type="str", default=None),
            lang=dict(type="str", default=None),
            scope=dict(type="str", default=None),
            limit=dict(type="int", default=50),
            exact=dict(type="bool", default=False),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=60),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
