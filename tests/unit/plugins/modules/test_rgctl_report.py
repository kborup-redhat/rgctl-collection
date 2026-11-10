import json
import pytest
from unittest.mock import patch, mock_open, call

FINDINGS = [{"check": "vuln", "severity": "high", "message": "CVE-2024-1234", "location": "foo"}]
INDEX = {"path": "/repo", "files_indexed": 95, "nodes": 500, "edges": 1200}


def _run(params):
    import rgctl_report as m
    mod = m.AnsibleModule.__new__(m.AnsibleModule)
    mod.params = params
    mod.check_mode = False
    with pytest.raises(SystemExit) as exc:
        m.run_module(mod)
    return exc.value.args[0]


def _params(**overrides):
    base = {
        "dest": "/tmp/report.json",
        "findings": FINDINGS,
        "format": "json",
        "index_info": INDEX,
        "metrics": {},
    }
    base.update(overrides)
    return base


def test_creates_report_when_missing():
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()) as mf:
        result = _run(_params())
    assert result["changed"] is True
    assert result["report_path"] == "/tmp/report.json"


def test_no_change_when_content_identical():
    content = json.dumps({"index": INDEX, "findings": FINDINGS, "metrics": {}}, indent=2)
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=content)):
        result = _run(_params())
    assert result["changed"] is False


def test_changed_when_findings_differ():
    old_content = json.dumps({"index": INDEX, "findings": []}, indent=2)
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=old_content)):
        result = _run(_params())
    assert result["changed"] is True


def test_markdown_format_contains_header_and_finding():
    written_data = []

    def fake_open(path, mode="r", **kw):
        m = mock_open()()
        m.write.side_effect = lambda data: written_data.append(data)
        m.__enter__ = lambda s: s
        m.__exit__ = lambda s, *a: False
        return m

    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", fake_open):
        result = _run(_params(dest="/tmp/report.md", format="markdown"))

    written = "".join(written_data)
    assert "# rgctl Security Report" in written
    assert "CVE-2024-1234" in written
    assert result["changed"] is True
