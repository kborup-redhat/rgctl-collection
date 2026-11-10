import json
import subprocess
import pytest
from unittest.mock import patch, MagicMock

STATUS_FRESH = json.dumps({
    "schema_version": 3, "command": "status", "status": "ok",
    "repo": "/repo", "index_current": True, "dirty_files": 0,
    "kantra_findings": False
})
STATUS_MISSING = json.dumps({
    "schema_version": 3, "command": "status", "status": "missing",
    "repo": "/repo", "kantra_findings": False
})
STATUS_STALE = json.dumps({
    "schema_version": 3, "command": "status", "status": "ok",
    "repo": "/repo", "index_current": False, "dirty_files": 3,
    "kantra_findings": False
})
DISCOVER_OK = json.dumps({
    "schema_version": 2, "command": "discover",
    "metrics": {
        "files_discovered": 100, "files_indexed": 95, "files_skipped": 5,
        "nodes_generated": 500, "edges_generated": 1200, "duration_ms": 3000
    }
})


def _run(params):
    import rgctl_discover as m
    mod = m.AnsibleModule.__new__(m.AnsibleModule)
    mod.params = params
    mod.check_mode = False
    with pytest.raises(SystemExit) as exc:
        m.run_module(mod)
    return exc.value.args[0]


def _params(**overrides):
    base = {
        "path": "/repo", "index_path": None, "force": False, "full": False,
        "files": [], "find_glob": None, "timeout": 600, "rgctl_bin": "rgctl",
        "with_cfg": False, "with_git": False, "git_since": None,
        "with_security": False, "with_taint": False, "taint_rules": None,
        "with_ast_skeleton": False, "with_dfg_loops": False,
        "with_harmonic": False, "with_universe": False,
        "with_limits": None, "scip": None, "write_json_graph": False,
        "export_migration_hints": False, "with_kantra": False,
        "kantra_rules": None, "kantra_catalog": None,
        "kantra_target": None, "kantra_index_only": False,
    }
    base.update(overrides)
    return base


def test_already_indexed_and_fresh_no_change():
    with patch("subprocess.run") as sp:
        sp.return_value = MagicMock(returncode=0, stdout=STATUS_FRESH)
        result = _run(_params())
    assert result["changed"] is False


def test_missing_index_triggers_discover():
    def side(cmd, **kw):
        if "status" in cmd:
            return MagicMock(returncode=0, stdout=STATUS_MISSING)
        return MagicMock(returncode=0, stdout=DISCOVER_OK)

    with patch("subprocess.run", side_effect=side):
        result = _run(_params())
    assert result["changed"] is True
    assert result["rgctl_index"]["files_indexed"] == 95
    assert result["rgctl_index"]["nodes"] == 500
    assert result["rgctl_index"]["edges"] == 1200


def test_stale_index_triggers_discover():
    def side(cmd, **kw):
        if "status" in cmd:
            return MagicMock(returncode=0, stdout=STATUS_STALE)
        return MagicMock(returncode=0, stdout=DISCOVER_OK)

    with patch("subprocess.run", side_effect=side):
        result = _run(_params())
    assert result["changed"] is True


def test_force_reruns_even_if_fresh():
    def side(cmd, **kw):
        if "status" in cmd:
            return MagicMock(returncode=0, stdout=STATUS_FRESH)
        return MagicMock(returncode=0, stdout=DISCOVER_OK)

    with patch("subprocess.run", side_effect=side):
        result = _run(_params(force=True))
    assert result["changed"] is True


def test_rgctl_not_in_path_fails_with_clear_message():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError) as exc:
            _run(_params())
    assert "rgctl" in str(exc.value).lower()


def test_discover_timeout_surfaces_clean_failure():
    def side(cmd, **kw):
        if "status" in cmd:
            return MagicMock(returncode=0, stdout=STATUS_MISSING)
        raise subprocess.TimeoutExpired(cmd, 600)

    with patch("subprocess.run", side_effect=side):
        with pytest.raises(RuntimeError) as exc:
            _run(_params())
    assert "timed out" in str(exc.value).lower()
