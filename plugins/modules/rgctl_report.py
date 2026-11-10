#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_report
short_description: Write rgctl analysis results to a file
description:
  - Writes security findings and index info to a JSON or Markdown report file.
  - Idempotent - only writes when content has changed (SHA256 comparison).
options:
  dest:
    description: Destination file path for the report.
    type: str
    required: true
  findings:
    description: List of security findings from rgctl_security.
    type: list
    required: true
  format:
    description: Output format.
    type: str
    choices: [json, markdown, html]
    default: json
  index_info:
    description: Index summary dict from rgctl_discover.
    type: dict
    default: {}
  metrics:
    description: Metrics dict from rgctl_metrics (optional).
    type: dict
    default: {}
  graphs:
    description: >
      Dict of named Mermaid diagram sources to embed. Keys are diagram titles,
      values are Mermaid source strings (from rgctl_graph.mermaid_source).
      Only used in html and markdown formats.
    type: dict
    default: {}
"""

RETURN = r"""
changed:
  description: Whether the report file was written or updated.
  type: bool
report_path:
  description: Path to the written report.
  type: str
"""

import hashlib
import json
import os

from ansible.module_utils.basic import AnsibleModule


def _build_json_content(index_info, findings, metrics):
    return json.dumps({"index": index_info, "findings": findings, "metrics": metrics}, indent=2)


def _graphs_markdown(graphs):
    if not graphs:
        return ""
    lines = ["", "## Graphs", ""]
    for title, source in graphs.items():
        lines += [f"### {title}", "", "```mermaid", source, "```", ""]
    return "\n".join(lines)


def _finding_summary(f):
    """Extract a human-readable verdict/status from a finding regardless of check type."""
    for key in ("exploitability", "verdict", "message"):
        if f.get(key):
            return str(f[key])
    return "n/a"


def _finding_detail(f):
    osv = f.get("osv_id", "")
    location = f.get("location", "")
    return osv or location or ""


def _build_markdown_content(index_info, findings, metrics, graphs=None):
    lines = ["# rgctl Security Report", ""]

    if index_info:
        lines += [
            "## Index Summary",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Path | {index_info.get('path', '')} |",
            f"| Files indexed | {index_info.get('files_indexed', 0)} |",
            f"| Graph nodes | {index_info.get('nodes', 0)} |",
            f"| Graph edges | {index_info.get('edges', 0)} |",
            f"| Index time | {index_info.get('duration_ms', 0)} ms |",
            "",
        ]

    lines += ["## Security Findings", "", f"Total: {len(findings)}", ""]

    if findings:
        lines += [
            "| Check | Severity | Result | Advisory / Location |",
            "|---|---|---|---|",
        ]
        for f in findings:
            check = f.get("check", "")
            sev = f.get("severity", "low")
            result = _finding_summary(f)
            detail = _finding_detail(f)
            lines.append(f"| {check} | {sev} | {result} | {detail} |")
    else:
        lines.append("No findings.")

    if metrics:
        lines += ["", "## Code Metrics", ""]
        if "pagerank_top" in metrics:
            lines += [
                "### Top Symbols by PageRank (highest coupling / change risk)",
                "",
                "| Rank | Symbol | Kind | Score |",
                "|---|---|---|---|",
            ]
            for i, s in enumerate(metrics["pagerank_top"][:10], 1):
                name = s.get("qualified_name", s.get("name", ""))
                kind = s.get("kind", "")
                score = f"{s.get('pagerank', 0):.6f}"
                lines.append(f"| {i} | `{name}` | {kind} | {score} |")
            lines.append("")
        if "communities" in metrics:
            c = metrics["communities"]
            lines += [
                "### Community Structure",
                "",
                f"| Metric | Value |",
                f"|---|---|",
                f"| Communities detected | {c.get('count', 0)} |",
                f"| Modularity score | {c.get('modularity', 0):.4f} |",
                f"| Symbols assigned | {c.get('assignments', 0)} |",
                "",
                "> Modularity > 0.3 indicates well-separated modules.",
                "",
            ]

    if graphs:
        lines.append(_graphs_markdown(graphs))

    return "\n".join(lines) + "\n"


def _sev_color(sev):
    return {"critical": "#c0392b", "high": "#e67e22",
            "medium": "#f39c12", "low": "#27ae60"}.get(sev, "#7f8c8d")


def _build_html_content(index_info, findings, metrics, graphs=None):
    sev_badge = lambda sev: (
        f'<span style="background:{_sev_color(sev)};color:#fff;'
        f'padding:2px 8px;border-radius:4px;font-size:0.85em">{sev}</span>'
    )

    sections = []

    # Index summary
    if index_info:
        rows = "".join(
            f"<tr><td>{k}</td><td><strong>{v}</strong></td></tr>"
            for k, v in [
                ("Path", index_info.get("path", "")),
                ("Files indexed", index_info.get("files_indexed", 0)),
                ("Graph nodes", index_info.get("nodes", 0)),
                ("Graph edges", index_info.get("edges", 0)),
                ("Index time", f"{index_info.get('duration_ms', 0)} ms"),
            ]
        )
        sections.append(f"""
        <section>
          <h2>Index Summary</h2>
          <table><tbody>{rows}</tbody></table>
        </section>""")

    # Security findings
    if findings:
        rows = "".join(
            f"<tr>"
            f"<td><code>{f.get('check','')}</code></td>"
            f"<td>{sev_badge(f.get('severity','low'))}</td>"
            f"<td>{_finding_summary(f)}</td>"
            f"<td>{_finding_detail(f)}</td>"
            f"</tr>"
            for f in findings
        )
        thead = "<tr><th>Check</th><th>Severity</th><th>Result</th><th>Advisory / Location</th></tr>"
        sections.append(f"""
        <section>
          <h2>Security Findings <span class="badge">{len(findings)}</span></h2>
          <table><thead>{thead}</thead><tbody>{rows}</tbody></table>
        </section>""")
    else:
        sections.append("""
        <section>
          <h2>Security Findings</h2>
          <p class="clean">&#10003; No findings.</p>
        </section>""")

    # Metrics
    if metrics:
        metric_sections = []
        if "pagerank_top" in metrics:
            rows = "".join(
                f"<tr>"
                f"<td>{i}</td>"
                f"<td><code>{s.get('qualified_name', s.get('name',''))}</code></td>"
                f"<td>{s.get('kind','')}</td>"
                f"<td>{s.get('pagerank',0):.6f}</td>"
                f"</tr>"
                for i, s in enumerate(metrics["pagerank_top"][:10], 1)
            )
            thead = "<tr><th>#</th><th>Symbol</th><th>Kind</th><th>PageRank Score</th></tr>"
            metric_sections.append(f"""
          <h3>Top Symbols by PageRank <small>(highest coupling / change risk)</small></h3>
          <table><thead>{thead}</thead><tbody>{rows}</tbody></table>""")

        if "communities" in metrics:
            c = metrics["communities"]
            rows = "".join([
                f"<tr><td>Communities detected</td><td><strong>{c.get('count',0)}</strong></td></tr>",
                f"<tr><td>Modularity score</td><td><strong>{c.get('modularity',0):.4f}</strong></td></tr>",
                f"<tr><td>Symbols assigned</td><td><strong>{c.get('assignments',0)}</strong></td></tr>",
            ])
            metric_sections.append(f"""
          <h3>Community Structure</h3>
          <table><tbody>{rows}</tbody></table>
          <p class="hint">Modularity &gt; 0.3 indicates well-separated modules.</p>""")

        sections.append(f"""
        <section>
          <h2>Code Metrics</h2>
          {"".join(metric_sections)}
        </section>""")

    # Graphs
    if graphs:
        graph_blocks = "".join(
            f'<h3>{title}</h3><div class="mermaid">{source}</div>'
            for title, source in graphs.items()
        )
        sections.append(f"""
        <section>
          <h2>Graphs</h2>
          {graph_blocks}
        </section>""")

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>rgctl Analysis Report</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true, theme:'neutral'}});</script>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto;
         padding: 0 1rem; color: #2c3e50; background: #f8f9fa; }}
  h1 {{ border-bottom: 2px solid #2c3e50; padding-bottom: .5rem; }}
  h2 {{ margin-top: 2rem; color: #34495e; }}
  h3 {{ color: #555; font-size: 1rem; margin-top: 1.5rem; }}
  small {{ color: #888; font-weight: normal; }}
  section {{ background: #fff; border-radius: 8px; padding: 1.5rem;
             margin: 1rem 0; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  table {{ border-collapse: collapse; width: 100%; margin-top: .75rem; font-size: .9rem; }}
  th {{ background: #34495e; color: #fff; padding: .5rem .75rem; text-align: left; }}
  td {{ padding: .4rem .75rem; border-bottom: 1px solid #ecf0f1; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f4f6f7; }}
  code {{ background: #ecf0f1; padding: 1px 5px; border-radius: 3px; font-size: .88em; }}
  .badge {{ background: #95a5a6; color: #fff; padding: 2px 8px;
            border-radius: 10px; font-size: .75em; vertical-align: middle; }}
  .clean {{ color: #27ae60; font-weight: bold; }}
  .hint {{ color: #888; font-size: .85em; margin-top: .5rem; }}
</style>
</head>
<body>
<h1>rgctl Analysis Report</h1>
{body}
</body>
</html>
"""


def _sha256(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def run_module(module):
    dest = module.params["dest"]
    findings = module.params["findings"]
    fmt = module.params["format"]
    index_info = module.params["index_info"] or {}
    metrics = module.params["metrics"] or {}
    graphs = module.params["graphs"] or {}

    if fmt == "json":
        new_content = _build_json_content(index_info, findings, metrics)
    elif fmt == "html":
        new_content = _build_html_content(index_info, findings, metrics, graphs)
    else:
        new_content = _build_markdown_content(index_info, findings, metrics, graphs)

    new_hash = _sha256(new_content)

    if os.path.exists(dest):
        try:
            with open(dest) as f:
                existing = f.read()
            if _sha256(existing) == new_hash:
                module.exit_json(changed=False, report_path=dest, msg="Report unchanged")
        except OSError:
            pass

    try:
        with open(dest, "w") as f:
            f.write(new_content)
    except OSError as e:
        module.fail_json(msg=f"Could not write report to {dest}: {e}")

    module.exit_json(changed=True, report_path=dest, msg=f"Report written to {dest}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            dest=dict(type="str", required=True),
            findings=dict(type="list", required=True),
            format=dict(type="str", choices=["json", "markdown", "html"], default="json"),
            index_info=dict(type="dict", default={}),
            metrics=dict(type="dict", default={}),
            graphs=dict(type="dict", default={}),
        ),
        supports_check_mode=False,
    )
    run_module(module)


if __name__ == "__main__":
    main()
