import json
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open

VULN_OUT = json.dumps([{
    "check": "vuln", "severity": "high",
    "message": "CVE-2024-1234", "location": "deps/foo"
}])
DEPS_OUT = json.dumps([{
    "check": "deps", "severity": "medium",
    "message": "outdated dep", "location": "Cargo.lock"
}])
TAINT_FILE = json.dumps({
    "id": 1, "variable": "user_input",
    "source_type": "http", "sink_type": "sql",
    "severity": 9, "vulnerable": True, "sanitizers": [],
    "source_line": 10, "sink_line": 42,
    "source_text": "req.body", "sink_text": "db.query",
    "path_lines": [10, 42], "path_statements": []
})


def _run(params):
    import rgctl_security as m
    mod = m.AnsibleModule.__new__(m.AnsibleModule)
    mod.params = params
    mod.check_mode = False
    with pytest.raises(SystemExit) as exc:
        m.run_module(mod)
    return exc.value.args[0]


def _params(**overrides):
    base = {
        "path": "/repo",
        "checks": ["vuln"],
        "severity_threshold": "medium",
        "rgctl_bin": "rgctl",
    }
    base.update(overrides)
    return base


def test_always_returns_changed_false():
    with patch("subprocess.run") as sp, \
         patch("os.path.isdir", return_value=False):
        sp.return_value = MagicMock(returncode=0, stdout="[]")
        result = _run(_params())
    assert result["changed"] is False


def test_vuln_findings_returned():
    with patch("subprocess.run") as sp, \
         patch("os.path.isdir", return_value=False):
        sp.return_value = MagicMock(returncode=0, stdout=VULN_OUT)
        result = _run(_params(severity_threshold="low"))
    assert any(f.get("check") == "vuln" for f in result["rgctl_security_findings"])


def test_above_threshold_count_correct():
    with patch("subprocess.run") as sp, \
         patch("os.path.isdir", return_value=False):
        sp.return_value = MagicMock(returncode=0, stdout=VULN_OUT)  # severity: high
        result = _run(_params(severity_threshold="medium"))
    assert result["above_threshold_count"] == 1


def test_taint_reads_dashboard_files():
    with patch("subprocess.run") as sp, \
         patch("os.path.isdir", return_value=True), \
         patch("os.listdir", return_value=["abc.json"]), \
         patch("builtins.open", mock_open(read_data=TAINT_FILE)):
        sp.return_value = MagicMock(returncode=0, stdout="[]")
        result = _run(_params(checks=["taint"], severity_threshold="low"))
    assert any(f.get("check") == "taint" for f in result["rgctl_security_findings"])


def test_below_threshold_still_returned_but_not_counted():
    low_finding = json.dumps([{
        "check": "deps", "severity": "low",
        "message": "minor issue", "location": "x"
    }])
    with patch("subprocess.run") as sp, \
         patch("os.path.isdir", return_value=False):
        sp.return_value = MagicMock(returncode=0, stdout=low_finding)
        result = _run(_params(checks=["deps"], severity_threshold="medium"))
    assert len(result["rgctl_security_findings"]) == 1
    assert result["above_threshold_count"] == 0
