#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_semantic
short_description: Natural-language semantic search over function symbols
description:
  - Runs Hamming nearest-neighbour search over the semantic index.
  - Requires the semantic index to have been built first with
    `rgctl semantic index` (not run by default during discover).
  - Fails with a clear message if the semantic index does not exist.
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  query:
    description: Natural-language or keyword query (e.g. "parse HTTP request body").
    type: str
    required: true
  limit:
    description: Maximum number of results.
    type: int
    default: 20
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
rgctl_semantic_results:
  description: List of matching symbol dicts.
  type: list
total:
  description: Number of results returned.
  type: int
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import run_rgctl, parse_json, check_error_envelope

_SEMANTIC_INDEX_HINT = (
    "rgctl semantic index not found. Build it first with: "
    "rgctl semantic index -r <repo_path>"
)


def run_module(module):
    p = module.params
    args = ["semantic", "query", p["query"], "--limit", str(p["limit"])]

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "semantic query") or {}

        # Semantic index missing produces a specific error
        if rc != 0:
            err_lower = (stderr + stdout).lower()
            if "semantic" in err_lower and ("index" in err_lower or "not found" in err_lower):
                module.fail_json(msg=_SEMANTIC_INDEX_HINT)
            module.fail_json(
                msg=f"rgctl semantic query failed (exit {rc}): {stderr or stdout}"
            )

        check_error_envelope(data, "semantic query")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    results = data.get("hits", data.get("results", []))

    module.exit_json(
        changed=False,
        rgctl_semantic_results=results,
        total=len(results),
        msg=f"{len(results)} semantic match(es) for query",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            query=dict(type="str", required=True),
            limit=dict(type="int", default=20),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=60),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
