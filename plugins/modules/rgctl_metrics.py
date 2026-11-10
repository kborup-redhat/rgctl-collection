#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_metrics
short_description: Collect code metrics from an indexed codebase with rgctl
description:
  - Runs rgctl metrics against an indexed codebase.
  - Collects PageRank hotspots, community structure, and optionally betweenness.
  - Always returns changed=false — analysis is read-only.
  - Requires the codebase to have been indexed with rgctl_discover first.
options:
  path:
    description: Absolute path to the indexed codebase.
    type: str
    required: true
  metrics:
    description: Which metrics to collect.
    type: list
    elements: str
    choices: [pagerank, communities, betweenness]
    default: [pagerank, communities]
  top_n:
    description: Number of top-ranked symbols to return in pagerank results.
    type: int
    default: 20
  rgctl_bin:
    description: Path to the rgctl binary.
    type: str
    default: rgctl
  timeout:
    description: Timeout in seconds for the metrics command.
    type: int
    default: 120
"""

RETURN = r"""
changed:
  description: Always false — metrics collection does not mutate state.
  type: bool
rgctl_metrics:
  description: Collected metrics.
  type: dict
  contains:
    pagerank_top:
      description: Top N symbols by PageRank (highest coupling/impact).
      type: list
    communities:
      description: Community detection summary (count, modularity, assignments).
      type: dict
    betweenness_top:
      description: Top N symbols by betweenness centrality (architectural bridges).
      type: list
"""

import json
import subprocess

from ansible.module_utils.basic import AnsibleModule


def _build_cmd(rgctl_bin, path, metrics, top_n):
    cmd = [rgctl_bin, "-r", path, "metrics", "-f", "json"]
    if "pagerank" in metrics:
        cmd.append("--pagerank")
    if "communities" in metrics:
        cmd.append("--communities")
    if "betweenness" in metrics:
        cmd.append("--betweenness")
    return cmd


def _run_metrics(path, metrics, top_n, rgctl_bin, timeout):
    cmd = _build_cmd(rgctl_bin, path, metrics, top_n)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "rgctl not found in PATH. For AAP, build and deploy the "
            "execution-environment image. For local machines, use "
            "rgctl.rgctl.rgctl_install first."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"rgctl metrics timed out after {timeout}s")

    if result.returncode != 0:
        raise RuntimeError(
            f"rgctl metrics failed (exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip() or 'no output'}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"rgctl metrics returned non-JSON output: {result.stdout[:200]}")

    return data


def _extract_metrics(data, metrics, top_n):
    out = {}

    if "pagerank" in metrics and "pagerank" in data:
        top = data["pagerank"].get("top", [])
        out["pagerank_top"] = top[:top_n]
        out["pagerank_converged"] = data["pagerank"].get("converged", False)
        out["pagerank_iterations"] = data["pagerank"].get("iterations", 0)

    if "communities" in metrics and "communities" in data:
        out["communities"] = data["communities"]

    if "betweenness" in metrics and "betweenness" in data:
        top = data["betweenness"].get("top", [])
        out["betweenness_top"] = top[:top_n]

    return out


def run_module(module):
    path = module.params["path"]
    metrics = module.params["metrics"]
    top_n = module.params["top_n"]
    rgctl_bin = module.params["rgctl_bin"]
    timeout = module.params["timeout"]

    try:
        data = _run_metrics(path, metrics, top_n, rgctl_bin, timeout)
        result = _extract_metrics(data, metrics, top_n)
    except RuntimeError as e:
        module.fail_json(msg=str(e))

    module.exit_json(
        changed=False,
        rgctl_metrics=result,
        msg=f"Metrics collected: {', '.join(metrics)}",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            metrics=dict(
                type="list",
                elements="str",
                default=["pagerank", "communities"],
            ),
            top_n=dict(type="int", default=20),
            rgctl_bin=dict(type="str", default="rgctl"),
            timeout=dict(type="int", default=120),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
