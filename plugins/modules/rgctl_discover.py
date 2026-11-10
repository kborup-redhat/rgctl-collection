#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_discover
short_description: Index a codebase with rgctl
description:
  - Runs rgctl discover against a local codebase.
  - Idempotent - checks rgctl status first and skips if index is current.
options:
  path:
    description: Absolute path to the codebase root.
    type: str
    required: true
  index_path:
    description: Override the default index storage location.
    type: str
    default: null
  force:
    description: Re-index even if the index is already current.
    type: bool
    default: false
  timeout:
    description: Timeout in seconds for the discover command.
    type: int
    default: 600
  rgctl_bin:
    description: Path to the rgctl binary.
    type: str
    default: rgctl
  with_cfg:
    description: >
      Build per-function CFG, dominators, and PDG into .rgctl/analysis/.
      Required for rgctl_slice, rgctl_inspect, and taint analysis.
      Significantly slower than a plain discover on large codebases.
    type: bool
    default: false
  with_git:
    description: Include git churn data (co-change edges, hotspot scores).
    type: bool
    default: false
"""

RETURN = r"""
changed:
  description: Whether the codebase was (re)indexed.
  type: bool
cfg_built:
  description: Whether CFG/PDG artifacts were built in this run.
  type: bool
rgctl_index:
  description: Index summary facts.
  type: dict
  contains:
    path:
      description: Indexed codebase path.
      type: str
    files_indexed:
      description: Number of files indexed.
      type: int
    nodes:
      description: Graph nodes generated.
      type: int
    edges:
      description: Graph edges generated.
      type: int
    duration_ms:
      description: Indexing duration in milliseconds.
      type: int
    index_path:
      description: Where the index is stored.
      type: str
"""

import json
import os
import subprocess

from ansible.module_utils.basic import AnsibleModule


def _run_cmd(cmd, timeout, fail_msg_prefix):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError(
            f"rgctl not found in PATH. For AAP, build and deploy the "
            f"execution-environment image. For local machines, use "
            f"rgctl.rgctl.rgctl_install first."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{fail_msg_prefix} timed out after {timeout}s")
    return result


def _get_status(path, index_path, rgctl_bin):
    """Return parsed status JSON dict, or None if unavailable."""
    cmd = [rgctl_bin, "status", path, "-f", "json"]
    if index_path:
        cmd += ["--index-path", index_path]
    result = _run_cmd(cmd, timeout=10, fail_msg_prefix="rgctl status")
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _status_is_fresh(status):
    if not status:
        return False
    return (
        status.get("status") == "ok"
        and status.get("index_current") is True
        and (status.get("dirty_files") or 0) == 0
    )


def _index_fact_from_status(path, index_path, status):
    """Build an rgctl_index fact from a status response (skip-path)."""
    return {
        "path": path,
        "files_indexed": status.get("nodes", 0),  # status exposes nodes/edges, not files
        "nodes": status.get("nodes", 0),
        "edges": status.get("edges", 0),
        "duration_ms": 0,
        "index_path": index_path or os.path.join(path, ".rgctl"),
    }


def _discover(path, index_path, with_cfg, with_git, rgctl_bin, timeout):
    cmd = [rgctl_bin, "discover", path, "-f", "json"]
    if index_path:
        cmd += ["--index-path", index_path]
    if with_cfg:
        cmd.append("--with-cfg")
    if with_git:
        cmd.append("--with-git")
    result = _run_cmd(cmd, timeout=timeout, fail_msg_prefix="rgctl discover")
    if result.returncode != 0:
        raise RuntimeError(f"rgctl discover failed: {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"rgctl discover returned non-JSON output: {result.stdout[:200]}")
    return data


def _build_index_fact(path, index_path, data):
    metrics = data.get("metrics", {})
    return {
        "path": path,
        "files_indexed": metrics.get("files_indexed", 0),
        "nodes": metrics.get("nodes_generated", 0),
        "edges": metrics.get("edges_generated", 0),
        "duration_ms": metrics.get("duration_ms", 0),
        "index_path": index_path or os.path.join(path, ".rgctl"),
    }


def run_module(module):
    path = module.params["path"]
    index_path = module.params["index_path"]
    force = module.params["force"]
    timeout = module.params["timeout"]
    rgctl_bin = module.params["rgctl_bin"]
    with_cfg = module.params["with_cfg"]
    with_git = module.params["with_git"]

    try:
        status = _get_status(path, index_path, rgctl_bin)
        cfg_ready = (status or {}).get("capabilities", {}).get("cfg_cpg", {}).get("ready", False)
        # Skip only when index is current AND CFG is already built (if requested)
        if not force and _status_is_fresh(status) and (not with_cfg or cfg_ready):
            index_fact = _index_fact_from_status(path, index_path, status)
            module.exit_json(
                changed=False,
                rgctl_index=index_fact,
                cfg_built=cfg_ready,
                msg="Index is current — skipping discover",
            )

        data = _discover(path, index_path, with_cfg, with_git, rgctl_bin, timeout)
        index_fact = _build_index_fact(path, index_path, data)
        module.exit_json(
            changed=True,
            rgctl_index=index_fact,
            cfg_built=with_cfg,
            msg=f"Codebase indexed" + (" (with CFG/PDG)" if with_cfg else ""),
        )

    except RuntimeError as e:
        module.fail_json(msg=str(e))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            index_path=dict(type="str", default=None),
            force=dict(type="bool", default=False),
            timeout=dict(type="int", default=600),
            rgctl_bin=dict(type="str", default="rgctl"),
            with_cfg=dict(type="bool", default=False),
            with_git=dict(type="bool", default=False),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
