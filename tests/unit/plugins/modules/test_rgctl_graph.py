import hashlib
import pytest
from unittest.mock import patch, mock_open


CALLERS_DATA = {
    "rgctl_callers": [
        {"id": "c1", "name": "processForm", "qualified_name": "OwnerController.processForm",
         "type": "function", "file": "OwnerController.java", "line": 90},
        {"id": "c2", "name": "$lambda_1", "qualified_name": "PetClinic.$lambda_1",
         "type": "function", "file": "PetClinic.java", "line": 10},
    ],
    "target": {"id": "t1", "name": "getName",
               "qualified_name": "NamedEntity.getName", "type": "function"},
    "total": 2,
    "changed": False,
}

CALLEES_DATA = {
    "rgctl_callees": [
        {"id": "e1", "name": "save", "qualified_name": "OwnerRepository.save",
         "type": "function", "file": "OwnerRepository.java", "line": 12},
    ],
    "total": 1,
    "changed": False,
}

BLAST_DATA = {
    "rgctl_blast_radius": {
        "target": {"symbol": "getName", "canonical_fqn": "NamedEntity::getName",
                   "file_path": "NamedEntity.java", "language": "java",
                   "signature": "public String getName()"},
        "metrics": {"direct_callers_count": 2, "impact_zone_size": 5, "score": 41.45},
        "topology": {
            "direct_callers": [
                {"id": "dc1", "fqn": "PetController.updatePetDetails", "file_path": "PetController.java"},
                {"id": "dc2", "fqn": "PetTypeFormatter.parse", "file_path": "PetTypeFormatter.java"},
            ]
        },
        "gatekeeping": {"policy_status": "SKIPPED", "violations": [], "handoffs": []},
    },
    "impact_score": 41.45,
    "changed": False,
}

RELATIONS_DATA = {
    "rgctl_relations": [
        {"source": {"id": "s1", "name": "Owner", "qualified_name": "org.example.Owner"},
         "target": {"id": "s2", "name": "Person", "qualified_name": "org.example.Person"},
         "type": "extends"},
    ],
    "target": {"id": "s1", "name": "Owner", "qualified_name": "org.example.Owner",
               "type": "class", "file": "Owner.java", "line": 48},
    "total": 1,
    "changed": False,
}


def _run(params):
    import rgctl_graph as m
    mod = m.AnsibleModule.__new__(m.AnsibleModule)
    mod.params = params
    mod.check_mode = False
    with pytest.raises(SystemExit) as exc:
        m.run_module(mod)
    return exc.value.args[0]


def _params(**overrides):
    base = {
        "dest": "/tmp/test.mmd",
        "data": CALLERS_DATA,
        "data_type": "callers",
        "title": "",
        "max_nodes": 30,
    }
    base.update(overrides)
    return base


# ── callers ──────────────────────────────────────────────────────────────────

def test_callers_generates_mermaid():
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        result = _run(_params())
    assert "flowchart" in result["mermaid_source"]
    assert result["changed"] is True


def test_callers_target_node_present():
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        result = _run(_params())
    assert "_target" in result["mermaid_source"]
    assert "getName" in result["mermaid_source"]


def test_callers_caller_arrows_to_target():
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        result = _run(_params())
    assert "--> _target" in result["mermaid_source"]


# ── idempotency ───────────────────────────────────────────────────────────────

def test_changed_false_when_identical():
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        result = _run(_params())
    mermaid = result["mermaid_source"]

    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=mermaid)):
        result2 = _run(_params())
    assert result2["changed"] is False


def test_changed_true_when_different():
    old_content = "flowchart TD\n    old --> node"
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=old_content)):
        result = _run(_params())
    assert result["changed"] is True


# ── node ID sanitization ──────────────────────────────────────────────────────

def test_node_id_sanitized():
    """Dots, $, spaces, parens in qualified names become underscores in node IDs."""
    data_with_special = {
        **CALLERS_DATA,
        "rgctl_callers": [
            {"id": "PetClinic.$lambda_1", "name": "$lambda_1",
             "qualified_name": "PetClinic.$lambda_1", "type": "function",
             "file": "PetClinic.java", "line": 10},
        ],
    }
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        result = _run(_params(data=data_with_special))
    # Node IDs must not contain $ or .
    for line in result["mermaid_source"].splitlines():
        if "-->" in line or "style" in line:
            node_part = line.split("[")[0].strip()
            assert "$" not in node_part, f"$ found in node ID: {line}"
            assert "." not in node_part, f". found in node ID: {line}"


# ── other data types ──────────────────────────────────────────────────────────

def test_callees_generates_mermaid():
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        result = _run(_params(data=CALLEES_DATA, data_type="callees"))
    assert "flowchart" in result["mermaid_source"]
    assert "_target -->" in result["mermaid_source"]


def test_blast_radius_generates_mermaid():
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        result = _run(_params(data=BLAST_DATA, data_type="blast_radius"))
    assert "flowchart" in result["mermaid_source"]
    assert "score:" in result["mermaid_source"]
    assert result["node_count"] == 2


def test_relations_generates_mermaid():
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        result = _run(_params(data=RELATIONS_DATA, data_type="relations"))
    assert "flowchart LR" in result["mermaid_source"]
    assert "extends" in result["mermaid_source"]


def test_title_appears_as_comment():
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        result = _run(_params(title="My Callers Graph"))
    assert "%% My Callers Graph" in result["mermaid_source"]


def test_max_nodes_caps_output():
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        result = _run(_params(max_nodes=1))
    assert result["node_count"] <= 1
