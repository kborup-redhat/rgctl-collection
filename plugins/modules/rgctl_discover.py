#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_discover
short_description: Index a codebase with rgctl
description:
  - Runs rgctl discover against a local codebase.
  - Idempotent - checks rgctl status first and skips if index is current
    (and CFG is already built if with_cfg was requested).
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
  full:
    description: Force a full (non-incremental) discovery pass.
    type: bool
    default: false
  files:
    description: Discover only these repo-relative paths (comma-joined → --files).
    type: list
    elements: str
    default: []
  find_glob:
    description: Glob filter — include only matching files (--find).
    type: str
    default: null
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
      Significantly slower on large codebases.
    type: bool
    default: false
  with_git:
    description: Include git churn data (co-change edges, hotspot scores).
    type: bool
    default: false
  git_since:
    description: >
      Git window for --with-git (e.g. "90.days", "2024-01-01").
      Only effective when with_git is true.
    type: str
    default: null
  with_security:
    description: Run Kantra security rule evaluation during discover.
    type: bool
    default: false
  with_taint:
    description: Include extra taint rule pack during discover.
    type: bool
    default: false
  taint_rules:
    description: Path to taint rules YAML file or directory (used with with_taint).
    type: str
    default: null
  with_ast_skeleton:
    description: Include AST skeleton pass.
    type: bool
    default: false
  with_dfg_loops:
    description: Include data-flow graph loop analysis.
    type: bool
    default: false
  with_harmonic:
    description: Include harmonic centrality computation.
    type: bool
    default: false
  with_universe:
    description: Enable universe-wide scan mode.
    type: bool
    default: false
  with_limits:
    description: >
      Resource limits for containers / small machines.
      Spec format: "max-mem-mb=4096,threads=1" (comma-separated key=value pairs).
      Pass an empty string to enable limits mode with defaults.
    type: str
    default: null
  scip:
    description: >
      Path to a SCIP protobuf index (.scip) to upgrade ambiguous call edges
      with compiler-exact symbol resolution.
    type: str
    default: null
  write_json_graph:
    description: Write a JSON graph sidecar alongside the binary snapshot.
    type: bool
    default: false
  with_kantra:
    description: Enable Kantra rule integration during discover.
    type: bool
    default: false
  kantra_rules:
    description: Path to Kantra rules directory (ruleset.yaml + *.yaml).
    type: str
    default: null
  kantra_catalog:
    description: Path to Kantra ruleset catalog root.
    type: str
    default: null
  kantra_target:
    description: Kantra target name to run.
    type: str
    default: null
  kantra_index_only:
    description: Index Kantra rules into the graph without running violation eval.
    type: bool
    default: false
  export_migration_hints:
    description: Export migration hints sidecar.
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
            "rgctl not found in PATH. For AAP, build and deploy the "
            "execution-environment image. For local machines, use "
            "rgctl.rgctl.rgctl_install first."
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
    return {
        "path": path,
        "files_indexed": status.get("nodes", 0),
        "nodes": status.get("nodes", 0),
        "edges": status.get("edges", 0),
        "duration_ms": 0,
        "index_path": index_path or os.path.join(path, ".rgctl"),
    }


def _build_discover_cmd(p):
    """Build the discover command from module params."""
    cmd = [p["rgctl_bin"], "discover", p["path"], "-f", "json"]

    if p["index_path"]:
        cmd += ["--index-path", p["index_path"]]
    if p["full"]:
        cmd.append("--full")
    if p["files"]:
        cmd += ["--files", ",".join(p["files"])]
    if p["find_glob"]:
        cmd += ["--find", p["find_glob"]]

    # Analysis passes
    if p["with_cfg"]:
        cmd.append("--with-cfg")
    if p["with_git"]:
        cmd.append("--with-git")
        if p["git_since"]:
            cmd += ["--git-since", p["git_since"]]
    if p["with_security"]:
        cmd.append("--with-security")
    if p["with_taint"]:
        cmd.append("--with-taint")
        if p["taint_rules"]:
            cmd += ["--taint-rules", p["taint_rules"]]
    if p["with_ast_skeleton"]:
        cmd.append("--with-ast-skeleton")
    if p["with_dfg_loops"]:
        cmd.append("--with-dfg-loops")
    if p["with_harmonic"]:
        cmd.append("--with-harmonic")
    if p["with_universe"]:
        cmd.append("--with-universe")

    # Resource limits
    if p["with_limits"] is not None:
        if p["with_limits"]:
            cmd += ["--with-limits", p["with_limits"]]
        else:
            cmd.append("--with-limits")

    # External data
    if p["scip"]:
        cmd += ["--scip", p["scip"]]
    if p["write_json_graph"]:
        cmd.append("--write-json-graph")
    if p["export_migration_hints"]:
        cmd.append("--export-migration-hints")

    # Kantra
    if p["with_kantra"]:
        cmd.append("--with-kantra")
    if p["kantra_rules"]:
        cmd += ["--kantra-rules", p["kantra_rules"]]
    if p["kantra_catalog"]:
        cmd += ["--kantra-catalog", p["kantra_catalog"]]
    if p["kantra_target"]:
        cmd += ["--kantra-target", p["kantra_target"]]
    if p["kantra_index_only"]:
        cmd.append("--kantra-index-only")

    return cmd


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


def _describe_passes(p):
    passes = []
    if p["with_cfg"]:
        passes.append("CFG/PDG")
    if p["with_git"]:
        passes.append("git")
    if p["with_security"]:
        passes.append("security")
    if p["with_taint"]:
        passes.append("taint")
    if p["with_kantra"] or p["kantra_rules"]:
        passes.append("kantra")
    if p["with_harmonic"]:
        passes.append("harmonic")
    return passes


def run_module(module):
    p = module.params
    path = p["path"]
    index_path = p["index_path"]
    with_cfg = p["with_cfg"]

    try:
        status = _get_status(path, index_path, p["rgctl_bin"])
        cfg_ready = (status or {}).get("capabilities", {}).get("cfg_cpg", {}).get("ready", False)

        if not p["force"] and _status_is_fresh(status) and (not with_cfg or cfg_ready):
            index_fact = _index_fact_from_status(path, index_path, status)
            module.exit_json(
                changed=False,
                rgctl_index=index_fact,
                cfg_built=cfg_ready,
                msg="Index is current — skipping discover",
            )

        cmd = _build_discover_cmd(p)
        result = _run_cmd(cmd, timeout=p["timeout"], fail_msg_prefix="rgctl discover")
        if result.returncode != 0:
            raise RuntimeError(f"rgctl discover failed: {result.stderr.strip()}")

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"rgctl discover returned non-JSON output: {result.stdout[:200]}")

        index_fact = _build_index_fact(path, index_path, data)
        passes = _describe_passes(p)
        suffix = f" (with {', '.join(passes)})" if passes else ""
        module.exit_json(
            changed=True,
            rgctl_index=index_fact,
            cfg_built=with_cfg,
            msg=f"Codebase indexed{suffix}",
        )

    except RuntimeError as e:
        module.fail_json(msg=str(e))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            index_path=dict(type="str", default=None),
            force=dict(type="bool", default=False),
            full=dict(type="bool", default=False),
            files=dict(type="list", elements="str", default=[]),
            find_glob=dict(type="str", default=None),
            timeout=dict(type="int", default=600),
            rgctl_bin=dict(type="str", default="rgctl"),
            # Analysis passes
            with_cfg=dict(type="bool", default=False),
            with_git=dict(type="bool", default=False),
            git_since=dict(type="str", default=None),
            with_security=dict(type="bool", default=False),
            with_taint=dict(type="bool", default=False),
            taint_rules=dict(type="str", default=None),
            with_ast_skeleton=dict(type="bool", default=False),
            with_dfg_loops=dict(type="bool", default=False),
            with_harmonic=dict(type="bool", default=False),
            with_universe=dict(type="bool", default=False),
            # Resource and data
            with_limits=dict(type="str", default=None),
            scip=dict(type="str", default=None),
            write_json_graph=dict(type="bool", default=False),
            export_migration_hints=dict(type="bool", default=False),
            # Kantra
            with_kantra=dict(type="bool", default=False),
            kantra_rules=dict(type="str", default=None),
            kantra_catalog=dict(type="str", default=None),
            kantra_target=dict(type="str", default=None),
            kantra_index_only=dict(type="bool", default=False),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
