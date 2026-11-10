"""Tests for the 6 query/analysis modules: find, callers, callees,
blast_radius, clones, relations."""

import json
import pytest
from unittest.mock import patch, MagicMock

# ── fixtures ────────────────────────────────────────────────────────────────

FIND_OUT = json.dumps({
    "entities": [
        {"id": "abc", "name": "Owner", "qualified_name": "org.example.Owner",
         "type": "class", "file": "Owner.java", "line": 48}
    ],
    "returned": 1, "total": 1, "schema_version": 2
})

FIND_EMPTY = json.dumps({"entities": [], "returned": 0, "total": 0, "schema_version": 2})

CALLERS_OUT = json.dumps({
    "callers": [
        {"id": "x1", "name": "processForm", "qualified_name": "OwnerController.processForm",
         "type": "function", "file": "OwnerController.java", "line": 90}
    ],
    "schema_version": 2
})

CALLEES_OUT = json.dumps({
    "callees": [
        {"id": "x2", "name": "save", "qualified_name": "OwnerRepository.save",
         "type": "function", "file": "OwnerRepository.java", "line": 12}
    ],
    "schema_version": 2, "total": 1
})

BLAST_OUT = json.dumps({
    "schema_version": 2,
    "target": {"symbol": "getName", "canonical_fqn": "NamedEntity::getName",
               "file_path": "NamedEntity.java", "language": "java",
               "signature": "public String getName()"},
    "metrics": {"direct_callers_count": 16, "impact_zone_size": 29, "score": 41.45},
    "topology": {"direct_callers": [{"fqn": "PetController.updatePetDetails",
                                     "file_path": "PetController.java", "id": "y1"}]},
    "gatekeeping": {"policy_status": "SKIPPED", "violations": [], "handoffs": []}
})

BLAST_NOT_FOUND = json.dumps({
    "ok": False, "error": "not_found", "error_code": "NOT_FOUND",
    "message": "Symbol 'bogus' not found",
    "recovery_command": "rgctl blast-radius bogus --file <PATH>",
    "schema_version": 1
})

CLONES_OUT = json.dumps({
    "group_count": 1, "graph_digest": "deadbeef",
    "filters": {"min_loc": 5},
    "groups": [
        {"hash": "aaa", "confidence": 1.0,
         "members": [
             {"id": "m1", "name": "ownerDetails", "file": "A.java",
              "start_line": 10, "end_line": 20, "loc": 11},
             {"id": "m2", "name": "ownerDetails", "file": "B.java",
              "start_line": 30, "end_line": 40, "loc": 11}
         ]}
    ]
})

RELATIONS_OUT = json.dumps({
    "schema_version": 2,
    "target": {"id": "t1", "name": "Owner", "qualified_name": "org.example.Owner",
               "type": "class", "file": "Owner.java", "line": 48},
    "edges": [
        {"id": "e1", "source": {"name": "OwnerController"}, "target": {"name": "Owner"},
         "type": "calls", "file": "OwnerController.java", "line": 55}
    ],
    "returned": 1, "total": 1
})


# ── helpers ──────────────────────────────────────────────────────────────────

def _run_module(module_name, params):
    import importlib
    m = importlib.import_module(module_name)
    mod = m.AnsibleModule.__new__(m.AnsibleModule)
    mod.params = params
    mod.check_mode = False
    with pytest.raises(SystemExit) as exc:
        m.run_module(mod)
    return exc.value.args[0]


def _sp(stdout, returncode=0):
    return MagicMock(returncode=returncode, stdout=stdout, stderr="")


# ── rgctl_find ───────────────────────────────────────────────────────────────

class TestFind:
    def _p(self, **kw):
        base = {"path": "/repo", "pattern": "Owner", "symbol_type": None,
                "file_glob": None, "lang": None, "scope": None,
                "limit": 50, "exact": False, "rgctl_bin": "rgctl", "timeout": 60}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(FIND_OUT)):
            r = _run_module("rgctl_find", self._p())
        assert r["changed"] is False

    def test_entities_returned(self):
        with patch("subprocess.run", return_value=_sp(FIND_OUT)):
            r = _run_module("rgctl_find", self._p())
        assert len(r["rgctl_find_results"]) == 1
        assert r["rgctl_find_results"][0]["name"] == "Owner"

    def test_total_returned(self):
        with patch("subprocess.run", return_value=_sp(FIND_OUT)):
            r = _run_module("rgctl_find", self._p())
        assert r["total"] == 1

    def test_empty_results_ok(self):
        with patch("subprocess.run", return_value=_sp(FIND_EMPTY)):
            r = _run_module("rgctl_find", self._p(pattern="Nonexistent"))
        assert r["rgctl_find_results"] == []

    def test_binary_missing_fails(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError) as exc:
                _run_module("rgctl_find", self._p())
        assert "rgctl" in str(exc.value).lower()


# ── rgctl_callers ─────────────────────────────────────────────────────────

class TestCallers:
    def _p(self, **kw):
        base = {"path": "/repo", "symbol": "getName", "depth": 1,
                "class_name": None, "file": None, "line": None,
                "limit": 50, "rgctl_bin": "rgctl", "timeout": 60}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(CALLERS_OUT)):
            r = _run_module("rgctl_callers", self._p())
        assert r["changed"] is False

    def test_callers_list_returned(self):
        with patch("subprocess.run", return_value=_sp(CALLERS_OUT)):
            r = _run_module("rgctl_callers", self._p())
        assert len(r["rgctl_callers"]) == 1
        assert r["rgctl_callers"][0]["name"] == "processForm"

    def test_binary_missing_fails(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError):
                _run_module("rgctl_callers", self._p())


# ── rgctl_callees ─────────────────────────────────────────────────────────

class TestCallees:
    def _p(self, **kw):
        base = {"path": "/repo", "symbol": "getName", "depth": 1,
                "class_name": None, "file": None, "line": None,
                "limit": 50, "rgctl_bin": "rgctl", "timeout": 60}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(CALLEES_OUT)):
            r = _run_module("rgctl_callees", self._p())
        assert r["changed"] is False

    def test_callees_list_returned(self):
        with patch("subprocess.run", return_value=_sp(CALLEES_OUT)):
            r = _run_module("rgctl_callees", self._p())
        assert r["rgctl_callees"][0]["name"] == "save"


# ── rgctl_blast_radius ────────────────────────────────────────────────────

class TestBlastRadius:
    def _p(self, **kw):
        base = {"path": "/repo", "symbol": "getName", "class_name": "NamedEntity",
                "file": None, "line": None, "depth": None, "summary": False,
                "classify_boundary": False, "rgctl_bin": "rgctl", "timeout": 120}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(BLAST_OUT)):
            r = _run_module("rgctl_blast_radius", self._p())
        assert r["changed"] is False

    def test_impact_score_returned(self):
        with patch("subprocess.run", return_value=_sp(BLAST_OUT)):
            r = _run_module("rgctl_blast_radius", self._p())
        assert r["impact_score"] == 41.45

    def test_topology_returned(self):
        with patch("subprocess.run", return_value=_sp(BLAST_OUT)):
            r = _run_module("rgctl_blast_radius", self._p())
        assert len(r["rgctl_blast_radius"]["topology"]["direct_callers"]) == 1

    def test_not_found_fails_with_clear_message(self):
        with patch("subprocess.run", return_value=_sp(BLAST_NOT_FOUND, returncode=1)):
            with pytest.raises(RuntimeError) as exc:
                _run_module("rgctl_blast_radius", self._p(symbol="bogus", class_name=None))
        assert "not_found" in str(exc.value).lower() or "not found" in str(exc.value).lower()


# ── rgctl_clones ──────────────────────────────────────────────────────────

class TestClones:
    def _p(self, **kw):
        base = {"path": "/repo", "mode": "exact", "symbol": None,
                "min_loc": 5, "exclude": [], "lang": None,
                "threshold": 0.85, "rgctl_bin": "rgctl", "timeout": 180}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(CLONES_OUT)):
            r = _run_module("rgctl_clones", self._p())
        assert r["changed"] is False

    def test_groups_returned(self):
        with patch("subprocess.run", return_value=_sp(CLONES_OUT)):
            r = _run_module("rgctl_clones", self._p())
        assert r["group_count"] == 1
        assert len(r["rgctl_clones"]) == 1
        assert len(r["rgctl_clones"][0]["members"]) == 2


# ── rgctl_relations ───────────────────────────────────────────────────────

class TestRelations:
    def _p(self, **kw):
        base = {"path": "/repo", "symbol": "Owner", "edge": "calls",
                "direction": "out", "depth": 1, "limit": 50,
                "class_name": None, "file": None, "line": None,
                "rgctl_bin": "rgctl", "timeout": 60}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(RELATIONS_OUT)):
            r = _run_module("rgctl_relations", self._p())
        assert r["changed"] is False

    def test_edges_returned(self):
        with patch("subprocess.run", return_value=_sp(RELATIONS_OUT)):
            r = _run_module("rgctl_relations", self._p())
        assert r["total"] == 1
        assert r["rgctl_relations"][0]["type"] == "calls"
