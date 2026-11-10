#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_semantic_index
short_description: Build the rgctl semantic search index
description:
  - Runs rgctl semantic index to build .rgctl/semantic_index.bin from
    function symbols, enabling semantic/NL search with rgctl_semantic.
  - Idempotent when incremental=true (default) — reuses embeddings for
    unchanged functions and only embeds new or changed ones.
  - Returns changed=true when at least one symbol was newly indexed;
    changed=false when all symbols were already embedded (skipped).
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  dimensions:
    description: Embedding dimensions (multiple of 8).
    type: int
    default: 256
  incremental:
    description: Reuse embeddings for unchanged functions (faster rebuilds).
    type: bool
    default: true
  rgctl_bin:
    description: Path to the rgctl binary.
    type: str
    default: rgctl
  timeout:
    description: Timeout in seconds. Semantic indexing can be slow on large repos.
    type: int
    default: 600
"""
RETURN = r"""
changed:
  description: True when at least one symbol was newly embedded.
  type: bool
indexed_count:
  description: Number of symbols newly embedded.
  type: int
skipped_count:
  description: Number of symbols skipped (unchanged, cached).
  type: int
artifact:
  description: Path to the produced semantic index artifact.
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common import (
    run_rgctl, parse_json, check_error_envelope
)


def run_module(module):
    p = module.params
    args = ["semantic", "index", "--dimensions", str(p["dimensions"])]
    if p["incremental"]:
        args.append("--incremental")

    try:
        rc, stdout, stderr = run_rgctl(args, p["path"], p["rgctl_bin"], p["timeout"])
        data = parse_json(stdout, "semantic index") or {}
        check_error_envelope(data, "semantic index")
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    build_stats = data.get("build_stats", {})
    indexed = build_stats.get("embedded", data.get("indexed", 0))
    skipped = build_stats.get("reused", data.get("skipped", 0))
    removed = build_stats.get("removed", 0)
    artifact = data.get("path", data.get("artifact", ".rgctl/semantic_index.bin"))

    module.exit_json(
        changed=(indexed > 0 or removed > 0),
        indexed_count=indexed,
        skipped_count=skipped,
        artifact=artifact,
        rgctl_semantic_index=data,
        msg=f"Semantic index: {indexed} embedded, {skipped} reused, {removed} removed — artifact: {artifact}",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            dimensions=dict(type="int", default=256),
            incremental=dict(type="bool", default=True),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=600),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
