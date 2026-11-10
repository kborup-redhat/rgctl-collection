#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_graph
short_description: Generate a Mermaid flowchart from rgctl query results
description:
  - Converts structured output from rgctl_callers, rgctl_callees,
    rgctl_blast_radius, or rgctl_relations into a Mermaid diagram written to a file.
  - Idempotent — only writes when content changes.
  - The output file can be embedded directly in GitHub/GitLab markdown or
    rendered by any Mermaid-compatible tool.
options:
  dest:
    description: Output file path (e.g. /tmp/callers.mmd or report.html).
    type: str
    required: true
  data:
    description: Result dict from rgctl_callers, rgctl_callees, rgctl_blast_radius, or rgctl_relations.
    type: dict
    required: true
  data_type:
    description: Which module produced the data.
    type: str
    choices: [callers, callees, blast_radius, relations]
    required: true
  title:
    description: Optional diagram title shown as a comment.
    type: str
    default: ""
  max_nodes:
    description: Maximum nodes to include (keeps diagrams readable).
    type: int
    default: 30
"""

RETURN = r"""
changed:
  type: bool
graph_path:
  description: Path to the written diagram file.
  type: str
node_count:
  description: Number of nodes included in the diagram.
  type: int
mermaid_source:
  description: The generated Mermaid source text.
  type: str
"""

import hashlib
import os
import re

from ansible.module_utils.basic import AnsibleModule


def _node_id(name):
    """Sanitize a name into a valid Mermaid node ID."""
    return re.sub(r"[^A-Za-z0-9_]", "_", str(name))


def _node_label(name, extra=""):
    """Format a Mermaid node label, escaping quotes."""
    name = str(name).replace('"', "'")
    if extra:
        extra = str(extra).replace('"', "'")
        return f'"{name}\\n{extra}"'
    return f'"{name}"'


def _short(qualified_name):
    """Return the last component of a qualified name for display."""
    return qualified_name.split(".")[-1] if "." in str(qualified_name) else str(qualified_name)


def _build_callers(data, max_nodes, title):
    callers = data.get("rgctl_callers", [])[:max_nodes]
    target_name = _short(data.get("target", {}).get("qualified_name", "target"))
    tid = "_target"
    lines = []
    if title:
        lines.append(f"%% {title}")
    lines.append("flowchart TD")
    lines.append(f"    {tid}[{_node_label(target_name)}]")
    lines.append(f"    style {tid} fill:#2c3e50,color:#fff,stroke:#2c3e50")
    for c in callers:
        name = _short(c.get("qualified_name", c.get("name", "caller")))
        nid = _node_id(c.get("id", name))
        lines.append(f"    {nid}[{_node_label(name)}] --> {tid}")
    return "\n".join(lines), len(callers)


def _build_callees(data, max_nodes, title):
    callees = data.get("rgctl_callees", [])[:max_nodes]
    target_name = _short(data.get("target", {}).get("qualified_name", "target"))
    tid = "_target"
    lines = []
    if title:
        lines.append(f"%% {title}")
    lines.append("flowchart TD")
    lines.append(f"    {tid}[{_node_label(target_name)}]")
    lines.append(f"    style {tid} fill:#2c3e50,color:#fff,stroke:#2c3e50")
    for c in callees:
        name = _short(c.get("qualified_name", c.get("name", "callee")))
        nid = _node_id(c.get("id", name))
        lines.append(f"    {tid} --> {nid}[{_node_label(name)}]")
    return "\n".join(lines), len(callees)


def _build_blast_radius(data, max_nodes, title):
    br = data.get("rgctl_blast_radius", {})
    target = br.get("target", {})
    target_name = target.get("symbol", target.get("canonical_fqn", "target"))
    score = data.get("impact_score", 0)
    topology = br.get("topology", {})
    direct_callers = topology.get("direct_callers", [])[:max_nodes]
    tid = "_target"
    lines = []
    if title:
        lines.append(f"%% {title}")
    lines.append("flowchart TD")
    lines.append(f"    {tid}[{_node_label(target_name, f'score: {score:.1f}')}]")
    lines.append(f"    style {tid} fill:#c0392b,color:#fff,stroke:#c0392b")
    node_count = 0
    for c in direct_callers:
        name = _short(c.get("fqn", c.get("id", "caller")))
        nid = _node_id(c.get("id", name))
        lines.append(f"    {nid}[{_node_label(name)}] --> {tid}")
        node_count += 1
    return "\n".join(lines), node_count


def _build_relations(data, max_nodes, title):
    edges = data.get("rgctl_relations", [])[:max_nodes]
    seed = data.get("target", {})
    seed_name = _short(seed.get("qualified_name", seed.get("name", "seed")))
    lines = []
    if title:
        lines.append(f"%% {title}")
    lines.append("flowchart LR")
    seen = set()
    if seed_name:
        sid = _node_id(seed.get("id", seed_name))
        lines.append(f"    {sid}[{_node_label(seed_name)}]")
        lines.append(f"    style {sid} fill:#2c3e50,color:#fff,stroke:#2c3e50")
        seen.add(sid)
    for e in edges:
        src = e.get("source", {})
        tgt = e.get("target", {})
        edge_type = e.get("type", "")
        src_name = _short(src.get("qualified_name", src.get("name", "src")))
        tgt_name = _short(tgt.get("qualified_name", tgt.get("name", "tgt")))
        src_id = _node_id(src.get("id", src_name))
        tgt_id = _node_id(tgt.get("id", tgt_name))
        if src_id not in seen:
            lines.append(f"    {src_id}[{_node_label(src_name)}]")
            seen.add(src_id)
        if tgt_id not in seen:
            lines.append(f"    {tgt_id}[{_node_label(tgt_name)}]")
            seen.add(tgt_id)
        label = f" --{edge_type}--> " if edge_type else " --> "
        lines.append(f"    {src_id}{label}{tgt_id}")
    return "\n".join(lines), len(edges)


def _build_mermaid(data, data_type, max_nodes, title):
    builders = {
        "callers": _build_callers,
        "callees": _build_callees,
        "blast_radius": _build_blast_radius,
        "relations": _build_relations,
    }
    return builders[data_type](data, max_nodes, title)


def _sha256(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def run_module(module):
    dest = module.params["dest"]
    data = module.params["data"]
    data_type = module.params["data_type"]
    title = module.params["title"] or ""
    max_nodes = module.params["max_nodes"]

    mermaid_source, node_count = _build_mermaid(data, data_type, max_nodes, title)

    new_hash = _sha256(mermaid_source)

    if os.path.exists(dest):
        try:
            with open(dest) as f:
                if _sha256(f.read()) == new_hash:
                    module.exit_json(
                        changed=False,
                        graph_path=dest,
                        node_count=node_count,
                        mermaid_source=mermaid_source,
                        msg="Graph unchanged",
                    )
        except OSError:
            pass

    try:
        with open(dest, "w") as f:
            f.write(mermaid_source)
    except OSError as e:
        module.fail_json(msg=f"Could not write graph to {dest}: {e}")

    module.exit_json(
        changed=True,
        graph_path=dest,
        node_count=node_count,
        mermaid_source=mermaid_source,
        msg=f"Graph written to {dest} ({node_count} node(s))",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            dest=dict(type="str", required=True),
            data=dict(type="dict", required=True),
            data_type=dict(type="str", required=True,
                           choices=["callers", "callees", "blast_radius", "relations"]),
            title=dict(type="str", default=""),
            max_nodes=dict(type="int", default=30),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
