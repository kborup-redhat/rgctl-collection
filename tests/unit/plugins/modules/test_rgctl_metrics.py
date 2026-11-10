import json
import pytest
from unittest.mock import patch, MagicMock

PAGERANK_OUT = json.dumps({
    "pagerank": {
        "converged": True,
        "iterations": 20,
        "max_delta": 1e-6,
        "top": [
            {"name": "BaseEntity", "qualified_name": "org.example.BaseEntity",
             "file_path": "src/main/java/BaseEntity.java", "kind": "class",
             "node": "abc-123", "pagerank": 0.00317}
        ]
    }
})

COMMUNITIES_OUT = json.dumps({
    "communities": {
        "assignments": 4654,
        "count": 4276,
        "modularity": 0.631
    },
    "schema_version": 1
})

COMBINED_OUT = json.dumps({
    "pagerank": {"converged": True, "iterations": 20, "max_delta": 1e-6, "top": [
        {"name": "BaseEntity", "qualified_name": "org.example.BaseEntity",
         "file_path": "src/main/java/BaseEntity.java", "kind": "class",
         "node": "abc-123", "pagerank": 0.00317}
    ]},
    "communities": {"assignments": 100, "count": 42, "modularity": 0.5},
    "schema_version": 1
})


def _run(params):
    import rgctl_metrics as m
    mod = m.AnsibleModule.__new__(m.AnsibleModule)
    mod.params = params
    mod.check_mode = False
    with pytest.raises(SystemExit) as exc:
        m.run_module(mod)
    return exc.value.args[0]


def _params(**overrides):
    base = {
        "path": "/repo",
        "metrics": ["pagerank", "communities"],
        "top_n": 20,
        "rgctl_bin": "rgctl",
        "timeout": 120,
    }
    base.update(overrides)
    return base


def test_always_returns_changed_false():
    with patch("subprocess.run") as sp:
        sp.return_value = MagicMock(returncode=0, stdout=COMBINED_OUT)
        result = _run(_params())
    assert result["changed"] is False


def test_pagerank_top_returned():
    with patch("subprocess.run") as sp:
        sp.return_value = MagicMock(returncode=0, stdout=COMBINED_OUT)
        result = _run(_params(metrics=["pagerank"]))
    assert "pagerank_top" in result["rgctl_metrics"]
    assert len(result["rgctl_metrics"]["pagerank_top"]) >= 1


def test_communities_summary_returned():
    with patch("subprocess.run") as sp:
        sp.return_value = MagicMock(returncode=0, stdout=COMBINED_OUT)
        result = _run(_params(metrics=["communities"]))
    assert "communities" in result["rgctl_metrics"]
    assert result["rgctl_metrics"]["communities"]["count"] == 42


def test_rgctl_not_in_path_fails_with_clear_message():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError) as exc:
            _run(_params())
    assert "rgctl" in str(exc.value).lower()


def test_nonzero_exit_fails_module():
    with patch("subprocess.run") as sp:
        sp.return_value = MagicMock(returncode=1, stdout="", stderr="index not found")
        with pytest.raises(RuntimeError) as exc:
            _run(_params())
    assert "failed" in str(exc.value).lower() or "exit" in str(exc.value).lower()
