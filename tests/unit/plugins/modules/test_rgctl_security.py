import json
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open

VULN_FINDING = json.dumps([{
    "check": "vuln_analyze", "severity": "high",
    "message": "CVE-2022-22965 reachable via PetController.initCreationForm",
    "exploitability": "exploitable", "location": "src/main/java/PetController.java"
}])
DEPS_FINDING = json.dumps([{
    "check": "deps_check", "severity": "medium",
    "verdict": "affected_candidate", "location": "pom.xml"
}])
TAINT_FINDING = json.dumps([{
    "variable": "user_input", "source_type": "http", "sink_type": "sql",
    "severity": 9, "vulnerable": True, "sanitizers": [],
    "source_line": 10, "sink_line": 42
}])


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
        "osv_file": "",
        "checks": [],
        "sink_symbols": [],
        "taint_depth": 8,
        "severity_threshold": "medium",
        "rgctl_bin": "rgctl",
        "timeout": 300,
    }
    base.update(overrides)
    return base


def test_always_returns_changed_false():
    result = _run(_params())
    assert result["changed"] is False


def test_vuln_check_skipped_when_no_osv_file():
    result = _run(_params(checks=["vuln_analyze"]))
    assert any("osv_file" in s for s in result["skipped_checks"])
    assert result["rgctl_security_findings"] == []


def test_taint_check_skipped_when_no_sink_symbols():
    result = _run(_params(checks=["taint"]))
    assert any("sink_symbols" in s for s in result["skipped_checks"])


def test_vuln_analyze_runs_with_osv_file():
    with patch("subprocess.run") as sp, \
         patch("os.path.exists", return_value=True):
        sp.return_value = MagicMock(returncode=0, stdout=VULN_FINDING)
        result = _run(_params(
            checks=["vuln_analyze"],
            osv_file="/tmp/advisory.json",
        ))
    assert any(f.get("check") == "vuln_analyze" for f in result["rgctl_security_findings"])


def test_nonzero_exit_fails_module_not_silent_empty():
    with patch("subprocess.run") as sp, \
         patch("os.path.exists", return_value=True):
        sp.return_value = MagicMock(returncode=1, stdout="", stderr="rgctl crashed")
        with pytest.raises(RuntimeError) as exc:
            _run(_params(checks=["vuln_analyze"], osv_file="/tmp/advisory.json"))
    assert "failed" in str(exc.value).lower() or "exit" in str(exc.value).lower()


def test_unknown_severity_string_does_not_crash():
    findings_with_info = json.dumps([{
        "severity": "info", "message": "low-priority", "location": "x"
    }])
    findings_with_uppercase = json.dumps([{
        "severity": "HIGH", "message": "uppercase", "location": "y"
    }])
    for payload in [findings_with_info, findings_with_uppercase]:
        with patch("subprocess.run") as sp, \
             patch("os.path.exists", return_value=True):
            sp.return_value = MagicMock(returncode=0, stdout=payload)
            result = _run(_params(
                checks=["vuln_analyze"],
                osv_file="/tmp/advisory.json",
                severity_threshold="low",
            ))
        assert isinstance(result["rgctl_security_findings"], list)


def test_taint_runs_per_sink_symbol():
    call_count = []

    def side(*args, **kwargs):
        call_count.append(1)
        return MagicMock(returncode=0, stdout=TAINT_FINDING)

    with patch("subprocess.run", side_effect=side):
        result = _run(_params(
            checks=["taint"],
            sink_symbols=["ObjectMapper.readValue", "Runtime.exec"],
        ))
    assert len(call_count) == 2


def test_above_threshold_count_correct():
    with patch("subprocess.run") as sp, \
         patch("os.path.exists", return_value=True):
        sp.return_value = MagicMock(returncode=0, stdout=VULN_FINDING)  # severity: high
        result = _run(_params(
            checks=["vuln_analyze"],
            osv_file="/tmp/advisory.json",
            severity_threshold="medium",
        ))
    assert result["above_threshold_count"] == 1
