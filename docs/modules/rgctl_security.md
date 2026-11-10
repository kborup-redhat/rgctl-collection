# rgctl.rgctl.rgctl_security

Run targeted security analysis against an indexed codebase using OSV advisories or taint tracing.

## Synopsis

Checks whether specific known vulnerabilities (from OSV advisory files) affect the codebase, and whether the vulnerable code paths are actually reachable. Unlike generic SCA tools, rgctl's vulnerability analysis uses the code graph to verify reachability — a dependency present in `pom.xml` but never called returns `not_affected`. Requires the codebase to be indexed with `rgctl_discover` first. Always returns `changed: false`.

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | str | yes | — | Absolute path to the indexed codebase |
| `osv_file` | str | no | `""` | Path to a local OSV advisory JSON file. Required for `vuln_analyze` and `deps_check` |
| `checks` | list | no | `[]` | Which checks to run: `vuln_analyze`, `deps_check`, `taint` |
| `sink_symbols` | list | no | `[]` | Sink symbols for taint analysis (e.g. `ObjectMapper.readValue`). Required for `taint` |
| `taint_depth` | int | no | `8` | Max call/data-flow depth for taint traversal |
| `severity_threshold` | str | no | `medium` | Minimum severity for `above_threshold_count`. One of: `low`, `medium`, `high`, `critical` |
| `rgctl_bin` | str | no | `rgctl` | Path to the rgctl binary |
| `timeout` | int | no | `300` | Timeout per check in seconds |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | Always `false` |
| `rgctl_security_findings` | list | All findings from all checks. Each finding includes `check`, `severity`, `osv_id`, `verdict` or `exploitability` |
| `above_threshold_count` | int | Number of findings at or above `severity_threshold` |
| `skipped_checks` | list | Checks that were skipped due to missing prerequisites (e.g. `osv_file` not provided) |

## Notes

**Getting an OSV advisory file:**

```bash
# Download by advisory ID from the OSV API
curl -o spring4shell.json https://api.osv.dev/v1/vulns/GHSA-36p3-wjmg-h94x

# Or by CVE
curl -o log4shell.json https://api.osv.dev/v1/vulns/CVE-2021-44228
```

**Check types:**

| Check | What it does | Requires |
|---|---|---|
| `deps_check` | Matches dependency manifests (`pom.xml`, `Cargo.toml`, etc.) against the OSV advisory. Fast — no graph traversal | `osv_file` |
| `vuln_analyze` | Full reachability pipeline: triage → deps → caller graph → taint. Verifies the vulnerable package is actually called. Returns OpenVEX output | `osv_file` |
| `taint` | Traces data flow from external sources to specified sink symbols. Requires `sink_symbols` and discover with `--with-cfg` | `sink_symbols` |

- Checks requiring missing prerequisites are automatically **skipped** (not failed) and appear in `skipped_checks`.
- A `verdict: not_affected` or `exploitability: not_affected` result means rgctl confirmed the codebase is not vulnerable to that specific advisory.
- Severity values are normalized: numeric scores (0–10) are mapped to `low/medium/high/critical`. Unknown strings like `"info"` or `"HIGH"` are safely lowercased and mapped.
- `taint` analysis requires `rgctl_discover` to have been run with `--with-cfg`. This is not yet exposed in the `rgctl_discover` module; run it manually or via the `rgctl_bin` shell if needed.

## Examples

```yaml
# Check for Spring4Shell (CVE-2022-22965)
- name: Download Spring4Shell advisory
  ansible.builtin.get_url:
    url: https://api.osv.dev/v1/vulns/GHSA-36p3-wjmg-h94x
    dest: /tmp/spring4shell.json

- name: Run security scan
  rgctl.rgctl.rgctl_security:
    path: /opt/analysis/spring-petclinic
    osv_file: /tmp/spring4shell.json
    checks:
      - deps_check
      - vuln_analyze
    severity_threshold: medium
  register: scan

- name: Fail on high/critical exploitable findings
  ansible.builtin.fail:
    msg: "{{ scan.above_threshold_count }} finding(s) above threshold"
  when: scan.above_threshold_count | int > 0

# Multiple advisories in a loop
- name: Check multiple advisories
  rgctl.rgctl.rgctl_security:
    path: /opt/analysis/my-app
    osv_file: "{{ item }}"
    checks: [deps_check, vuln_analyze]
    severity_threshold: high
  loop:
    - /tmp/advisories/log4shell.json
    - /tmp/advisories/spring4shell.json
  register: multi_scan
```
