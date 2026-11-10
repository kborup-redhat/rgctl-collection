"""Tests for: rgctl_update, rgctl_inventory, rgctl_check, rgctl_semantic, rgctl_review."""

import json
import importlib
import pytest
from unittest.mock import patch, MagicMock

# ── fixtures ────────────────────────────────────────────────────────────────

UPDATE_CHANGED = json.dumps({
    "schema_version": 2, "command": "update",
    "metrics": {"files_indexed": 3, "files_discovered": 3, "files_skipped": 0,
                "nodes_generated": 50, "edges_generated": 120, "duration_ms": 200}
})
UPDATE_NOOP = json.dumps({
    "schema_version": 2, "command": "update",
    "metrics": {"files_indexed": 0, "files_discovered": 0, "files_skipped": 5,
                "nodes_generated": 0, "edges_generated": 0, "duration_ms": 10}
})

INVENTORY_OUT = json.dumps({
    "by": "type",
    "counts": [
        {"key": "function", "count": 239},
        {"key": "class", "count": 2716},
        {"key": "import", "count": 1699},
    ]
})

CHECK_PASS = json.dumps({"violations": [], "warnings": [], "status": "pass"})
CHECK_FAIL = json.dumps({
    "violations": [
        {"rule": "no-direct-db-calls", "symbol": "OwnerController.findOwner",
         "severity": "error", "message": "Direct DB call outside repository layer"}
    ],
    "warnings": [],
    "status": "fail"
})

SEMANTIC_OUT = json.dumps({
    "hits": [
        {"name": "parseBody", "qualified_name": "HttpParser.parseBody",
         "file": "HttpParser.java", "line": 42, "score": 0.95},
        {"name": "readRequest", "qualified_name": "RequestHandler.readRequest",
         "file": "RequestHandler.java", "line": 18, "score": 0.88}
    ]
})

SEMANTIC_NO_INDEX = ""  # empty stdout + non-zero rc + stderr about index

REVIEW_OUT = json.dumps({
    "schema_version": 1,
    "added": [
        {"path": "PetController -> OwnerRepository -> findById", "risk": "low"}
    ],
    "removed": [],
    "summary": {"added": 1, "removed": 0}
})


# ── helpers ──────────────────────────────────────────────────────────────────

def _run(module_name, params):
    m = importlib.import_module(module_name)
    mod = m.AnsibleModule.__new__(m.AnsibleModule)
    mod.params = params
    mod.check_mode = False
    with pytest.raises(SystemExit) as exc:
        m.run_module(mod)
    return exc.value.args[0]


def _sp(stdout, returncode=0, stderr=""):
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


# ── rgctl_update ─────────────────────────────────────────────────────────────

class TestUpdate:
    def _p(self, **kw):
        base = {"path": "/repo", "files": [], "rgctl_bin": "rgctl", "timeout": 300}
        base.update(kw)
        return base

    def test_changed_true_when_files_indexed(self):
        with patch("subprocess.run", return_value=_sp(UPDATE_CHANGED)):
            r = _run("rgctl_update", self._p())
        assert r["changed"] is True

    def test_changed_false_when_nothing_updated(self):
        with patch("subprocess.run", return_value=_sp(UPDATE_NOOP)):
            r = _run("rgctl_update", self._p())
        assert r["changed"] is False

    def test_metrics_returned(self):
        with patch("subprocess.run", return_value=_sp(UPDATE_CHANGED)):
            r = _run("rgctl_update", self._p())
        assert r["rgctl_update"]["metrics"]["files_indexed"] == 3

    def test_binary_missing_fails(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError) as exc:
                _run("rgctl_update", self._p())
        assert "rgctl" in str(exc.value).lower()


# ── rgctl_inventory ───────────────────────────────────────────────────────────

class TestInventory:
    def _p(self, **kw):
        base = {"path": "/repo", "by": "type", "limit": 50,
                "prefix": None, "rgctl_bin": "rgctl", "timeout": 60}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(INVENTORY_OUT)):
            r = _run("rgctl_inventory", self._p())
        assert r["changed"] is False

    def test_counts_returned(self):
        with patch("subprocess.run", return_value=_sp(INVENTORY_OUT)):
            r = _run("rgctl_inventory", self._p())
        assert len(r["rgctl_inventory"]) == 3
        assert r["rgctl_inventory"][0]["key"] == "function"

    def test_total_symbols_summed(self):
        with patch("subprocess.run", return_value=_sp(INVENTORY_OUT)):
            r = _run("rgctl_inventory", self._p())
        assert r["total_symbols"] == 239 + 2716 + 1699

    def test_binary_missing_fails(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError):
                _run("rgctl_inventory", self._p())


# ── rgctl_check ───────────────────────────────────────────────────────────────

class TestCheck:
    def _p(self, **kw):
        base = {"path": "/repo", "policy_file": "/etc/policy.yml",
                "base_ref": None, "head_ref": None, "strict": False,
                "rgctl_bin": "rgctl", "timeout": 120}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(CHECK_PASS)):
            r = _run("rgctl_check", self._p())
        assert r["changed"] is False

    def test_passed_true_when_no_violations(self):
        with patch("subprocess.run", return_value=_sp(CHECK_PASS)):
            r = _run("rgctl_check", self._p())
        assert r["passed"] is True
        assert r["violation_count"] == 0

    def test_passed_false_when_violations_found(self):
        with patch("subprocess.run", return_value=_sp(CHECK_FAIL)):
            r = _run("rgctl_check", self._p())
        assert r["passed"] is False
        assert r["violation_count"] == 1

    def test_violations_do_not_fail_module(self):
        # check failures should not raise — playbook decides
        with patch("subprocess.run", return_value=_sp(CHECK_FAIL)):
            r = _run("rgctl_check", self._p())
        assert "violation" in r["msg"].lower()

    def test_binary_missing_fails(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError):
                _run("rgctl_check", self._p())


# ── rgctl_semantic ────────────────────────────────────────────────────────────

class TestSemantic:
    def _p(self, **kw):
        base = {"path": "/repo", "query": "parse HTTP request body",
                "limit": 20, "rgctl_bin": "rgctl", "timeout": 60}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(SEMANTIC_OUT)):
            r = _run("rgctl_semantic", self._p())
        assert r["changed"] is False

    def test_results_returned(self):
        with patch("subprocess.run", return_value=_sp(SEMANTIC_OUT)):
            r = _run("rgctl_semantic", self._p())
        assert len(r["rgctl_semantic_results"]) == 2
        assert r["total"] == 2

    def test_missing_index_gives_clear_error(self):
        with patch("subprocess.run", return_value=_sp(
            "", returncode=1, stderr="semantic index not found"
        )):
            with pytest.raises(RuntimeError) as exc:
                _run("rgctl_semantic", self._p())
        assert "semantic" in str(exc.value).lower()

    def test_binary_missing_fails(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError):
                _run("rgctl_semantic", self._p())


# ── rgctl_review ──────────────────────────────────────────────────────────────

class TestReview:
    def _p(self, **kw):
        base = {"path": "/repo", "base_snapshot": "/snap/base",
                "head_snapshot": "/snap/head",
                "rgctl_bin": "rgctl", "timeout": 180}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(REVIEW_OUT)):
            r = _run("rgctl_review", self._p())
        assert r["changed"] is False

    def test_added_removed_counts(self):
        with patch("subprocess.run", return_value=_sp(REVIEW_OUT)):
            r = _run("rgctl_review", self._p())
        assert r["added_paths"] == 1
        assert r["removed_paths"] == 0

    def test_full_result_returned(self):
        with patch("subprocess.run", return_value=_sp(REVIEW_OUT)):
            r = _run("rgctl_review", self._p())
        assert "added" in r["rgctl_review_paths"]

    def test_binary_missing_fails(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError):
                _run("rgctl_review", self._p())
