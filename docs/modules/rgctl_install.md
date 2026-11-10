# rgctl.rgctl.rgctl_install

Install the rgctl binary on a local Linux machine.

## Synopsis

Downloads the rgctl binary from GitHub releases, verifies its SHA256 checksum, and installs it to the target path. Idempotent — skips installation if the correct version is already present. Only use this module for **local machines**; for AAP, bake rgctl into the Execution Environment image instead (see `execution-environment/`).

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `version` | str | no | `latest` | Version to install. `latest` resolves via GitHub API at play time. Use `skip-install` to assert the binary must already be in PATH (useful in EE environments to get a clear error rather than a silent download). |
| `install_path` | str | no | `/usr/local/bin` | Directory where the `rgctl` binary is placed. |
| `arch` | str | no | `x86_64` | CPU architecture. Only `x86_64` Linux binaries are published; `aarch64` is macOS-only. |

## Return Values

| Key | Type | Description |
|---|---|---|
| `changed` | bool | `true` if the binary was installed or upgraded. |
| `rgctl_version_installed` | str | The version string that is now installed. |
| `msg` | str | Human-readable result. |

## Notes

- Supports `check_mode` — reports whether it would install without actually doing so.
- `version: latest` calls the GitHub API on every run; this counts against the 60 unauthenticated requests/hour rate limit. Pin a version in long-running playbooks.
- Only Linux x86_64 is supported. For other architectures, install rgctl manually.
- For AAP, do **not** use this module. Build the EE from `execution-environment/execution-environment.yml` with `ansible-builder`.

## Examples

```yaml
# Install the latest version
- name: Install rgctl
  rgctl.rgctl.rgctl_install:
    version: latest

# Pin to a specific version
- name: Install rgctl 0.4.26
  rgctl.rgctl.rgctl_install:
    version: "0.4.26"
    install_path: /usr/local/bin

# Assert rgctl is already present (EE / pre-provisioned machine)
- name: Verify rgctl is in PATH (EE mode)
  rgctl.rgctl.rgctl_install:
    version: skip-install
```
