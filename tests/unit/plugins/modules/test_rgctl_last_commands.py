"""Tests for the final 4 modules: diff, slice, inspect, semantic_index."""

import json
import pytest
from unittest.mock import patch, MagicMock

# ── fixtures ────────────────────────────────────────────────────────────────

DIFF_OUT = json.dumps({
    "schema_version": 1,
    "command": "diff",
    "added": [
        {"id": "n1", "name": "newMethod", "qualified_name": "Foo.newMethod",
         "type": "function", "file": "Foo.java", "line": 10}
    ],
    "removed": [],
    "changed": [
        {"id": "n2", "name": "existingMethod", "qualified_name": "Bar.existingMethod",
         "type": "function", "file": "Bar.java", "line": 42}
    ],
    "stats": {"added": 1, "removed": 0, "changed": 1}
})

SLICE_OUT = json.dumps({
    "schema_version": 1,
    "command": "slice",
    "file": "Owner.java",
    "line": 65,
    "variable": "name",
    "direction": "backward",
    "slice": [
        {"line": 60, "statement": "String name = entity.getName();"},
        {"line": 65, "statement": "if (name == null) {"}
    ],
    "length": 2
})

INSPECT_OUT = json.dumps({
    "schema_version": 1,
    "command": "inspect",
    "subcommand": "cfg",
    "symbol": "getName",
    "blocks": [
        {"id": "b1", "kind": "entry", "statements": ["return name;"],
         "successors": [], "predecessors": []}
    ],
    "block_count": 1
})

SEMANTIC_INDEX_OUT = json.dumps({
    "schema_version": 2,
    "build_stats": {"embedded": 239, "reused": 0, "removed": 0, "total": 239},
    "functions_indexed": 239,
    "dimensions": 256,
    "path": ".rgctl/semantic_index.bin",
    "model_id": "vocab-accumulate-v2",
    "graph_digest": "deadbeef"
})


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


# ── rgctl_diff ───────────────────────────────────────────────────────────────

class TestDiff:
    def _p(self, **kw):
        base = {"path": "/repo", "base_snapshot": "/snap/base",
                "head_snapshot": "/snap/head",
                "rgctl_bin": "rgctl", "timeout": 120}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(DIFF_OUT)):
            r = _run_module("rgctl_diff", self._p())
        assert r["changed"] is False

    def test_added_removed_counts(self):
        with patch("subprocess.run", return_value=_sp(DIFF_OUT)):
            r = _run_module("rgctl_diff", self._p())
        assert r["added_count"] == 1
        assert r["removed_count"] == 0
        assert r["changed_count"] == 1

    def test_full_result_returned(self):
        with patch("subprocess.run", return_value=_sp(DIFF_OUT)):
            r = _run_module("rgctl_diff", self._p())
        assert len(r["rgctl_diff"]["added"]) == 1
        assert r["rgctl_diff"]["added"][0]["name"] == "newMethod"

    def test_binary_missing_fails(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError):
                _run_module("rgctl_diff", self._p())


# ── rgctl_slice ────────────────────────────────────────────────────────────

class TestSlice:
    def _p(self, **kw):
        base = {"path": "/repo", "file": "Owner.java", "line": 65,
                "variable": "name", "direction": "backward",
                "function": None, "taint": False, "with_alias": False,
                "rgctl_bin": "rgctl", "timeout": 120}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(SLICE_OUT)):
            r = _run_module("rgctl_slice", self._p())
        assert r["changed"] is False

    def test_slice_statements_returned(self):
        with patch("subprocess.run", return_value=_sp(SLICE_OUT)):
            r = _run_module("rgctl_slice", self._p())
        assert r["slice_length"] == 2
        assert len(r["rgctl_slice"]["slice"]) == 2

    def test_binary_missing_fails(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError):
                _run_module("rgctl_slice", self._p())


# ── rgctl_inspect ─────────────────────────────────────────────────────────

class TestInspect:
    def _p(self, **kw):
        base = {"path": "/repo", "symbol": "getName", "subcommand": "cfg",
                "class_name": None, "file": None, "line": None, "prune": False,
                "rgctl_bin": "rgctl", "timeout": 120}
        base.update(kw)
        return base

    def test_changed_false(self):
        with patch("subprocess.run", return_value=_sp(INSPECT_OUT)):
            r = _run_module("rgctl_inspect", self._p())
        assert r["changed"] is False

    def test_blocks_returned(self):
        with patch("subprocess.run", return_value=_sp(INSPECT_OUT)):
            r = _run_module("rgctl_inspect", self._p())
        assert r["rgctl_inspect"]["block_count"] == 1
        assert r["rgctl_inspect"]["blocks"][0]["kind"] == "entry"

    def test_binary_missing_fails(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError):
                _run_module("rgctl_inspect", self._p())


# ── rgctl_semantic_index ──────────────────────────────────────────────────

class TestSemanticIndex:
    def _p(self, **kw):
        base = {"path": "/repo", "dimensions": 256, "incremental": True,
                "rgctl_bin": "rgctl", "timeout": 600}
        base.update(kw)
        return base

    def test_changed_true_when_indexed(self):
        with patch("subprocess.run", return_value=_sp(SEMANTIC_INDEX_OUT)):
            r = _run_module("rgctl_semantic_index", self._p())
        assert r["changed"] is True
        assert r["indexed_count"] == 239

    def test_changed_false_when_nothing_indexed(self):
        all_reused = json.loads(SEMANTIC_INDEX_OUT)
        all_reused["build_stats"] = {"embedded": 0, "reused": 239, "removed": 0, "total": 239}
        with patch("subprocess.run", return_value=_sp(json.dumps(all_reused))):
            r = _run_module("rgctl_semantic_index", self._p())
        assert r["changed"] is False

    def test_artifact_path_returned(self):
        with patch("subprocess.run", return_value=_sp(SEMANTIC_INDEX_OUT)):
            r = _run_module("rgctl_semantic_index", self._p())
        assert "semantic_index.bin" in r["artifact"]

    def test_binary_missing_fails(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError):
                _run_module("rgctl_semantic_index", self._p())
