# rgctl.rgctl Collection — Extension Guide

This file tells Claude how to extend this collection with new modules.
Read it before adding any new rgctl command group.

---

## Collection Structure

```
plugins/modules/          ← one Python file per module
roles/analyze_pipeline/   ← the main pipeline role
playbooks/                ← standalone playbooks (install.yml etc.)
execution-environment/    ← AAP EE build artefacts
tests/unit/plugins/modules/ ← pytest unit tests, one file per module
```

---

## Adding a New Module

New modules wrap an rgctl command group (e.g., `callers`, `blast-radius`, `find`).

### 1. Create the file

`plugins/modules/rgctl_<command>.py`

Copy the structure from an existing module. Every module has these sections:
- `DOCUMENTATION` — docstring for ansible-doc
- `RETURN` — describes return values
- `run_module(module)` — the entry point called by `main()`
- `main()` — creates `AnsibleModule` and calls `run_module`

### 2. Argument spec pattern

```python
module = AnsibleModule(
    argument_spec=dict(
        path=dict(type="str", required=True),
        symbol=dict(type="str", required=True),
        rgctl_bin=dict(type="str", default="rgctl"),
        timeout=dict(type="int", default=120),
    ),
    supports_check_mode=False,
)
```

Always include `rgctl_bin` and `timeout` as optional params.

### 3. Calling rgctl

Always use this pattern — parse stdout only, never stderr:

```python
import subprocess

try:
    result = subprocess.run(
        [rgctl_bin, "callers", symbol, "-f", "json"],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=path,
    )
except FileNotFoundError:
    raise RuntimeError(
        "rgctl not found in PATH. For AAP, build and deploy the "
        "execution-environment image. For local machines, use "
        "rgctl.rgctl.rgctl_install first."
    )
except subprocess.TimeoutExpired:
    raise RuntimeError(f"rgctl callers timed out after {timeout}s")
```

Then parse `result.stdout` as JSON. Never parse `result.stderr`.

### 4. Idempotency rules

| Command type | Is idempotent? | How |
|---|---|---|
| Read-only query (`find`, `callers`, `relations`) | Yes — `changed: false` always | Always return `changed=False` |
| State-mutating (`discover`, `update`) | Yes — check state first | Run `rgctl status -f json`, skip if `index_current: true` and `dirty_files: 0` |
| Install (`install`) | Yes — check version | Run `rgctl --version`, skip if version matches |
| Analysis (`security`, `blast-radius`) | Yes — read-only | Always return `changed=False` |

### 5. Return value shape

Every module returns at minimum:
```python
module.exit_json(
    changed=False,            # or True
    rgctl_<command>=result,   # primary result key: dict or list
    msg="Human-readable summary",
)
```

For error cases, always use:
```python
module.fail_json(msg="Clear error message pointing to cause and fix")
```

Wrap all `RuntimeError` calls from rgctl helpers in a `try/except RuntimeError` and call `module.fail_json`.

### 6. Write the test first (TDD)

Create `tests/unit/plugins/modules/test_rgctl_<command>.py`.

Use this `_run` helper pattern — it uses `FakeAnsibleModule` from conftest:

```python
def _run(params):
    import rgctl_<command> as m
    mod = m.AnsibleModule.__new__(m.AnsibleModule)
    mod.params = params
    mod.check_mode = False
    with pytest.raises(SystemExit) as exc:
        m.run_module(mod)
    return exc.value.args[0]
```

For tests that expect `fail_json` (RuntimeError), call `_run` inside `pytest.raises(RuntimeError)`:

```python
def test_binary_missing():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError) as exc:
            _run(_params())
    assert "rgctl" in str(exc.value).lower()
```

Minimum tests for any new module:
1. Happy path — correct return value
2. `changed: false` / `changed: true` — verify idempotency logic
3. Binary not in PATH — fail with EE guidance message
4. Timeout — fail with "timed out" in message

Run all tests before committing:
```bash
python -m pytest tests/unit/ -v
```

---

## Adding a New Role

If the new module is part of a workflow, add it to the `analyze_pipeline` role in
`roles/analyze_pipeline/tasks/main.yml`. Add any new variables to `defaults/main.yml`.

For a standalone workflow role, create `roles/<role_name>/` with the same structure.

---

## Upgrading rgctl Version

1. Update `RGCTL_VERSION` in `execution-environment/execution-environment.yml`
2. Update `ARG RGCTL_VERSION` default in `execution-environment/Containerfile`
3. Rebuild the EE: `ansible-builder build -t rgctl-ee:latest -f execution-environment/execution-environment.yml`
4. Push the new EE to your registry and update AAP job templates to use it

The `rgctl_install` module's `version: "latest"` resolves dynamically at runtime for local machines — no change needed there.

---

## rgctl JSON Output Schemas (key facts)

| Command | schema_version | Key output fields |
|---|---|---|
| `status` | 3 | `status` ("ok"\|"missing"), `index_current` (bool), `dirty_files` (int) |
| `discover` | 2 | `metrics.files_indexed`, `metrics.nodes_generated`, `metrics.edges_generated`, `metrics.duration_ms` |
| `security`/`vuln`/`deps` | 1 | list of findings: `severity`, `message`, `location` |
| `taint` | 1 | writes to `.rgctl/dashboard/taint/*.json` — read with `os.listdir` |

Always pass `-f json` to get structured output. Parse stdout only. Exit code non-zero may still yield valid JSON findings on stdout.

Error envelope (ambiguous symbol):
```json
{"schema_version": 2, "error": "ambiguous_symbol", "candidates": [...]}
```
Check for `"error"` key in parsed JSON before treating output as findings.

---

## Running the Full Test Suite

```bash
python -m pytest tests/unit/ -v
```

All 20 tests should pass. Add new tests before merging.
