#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
module: rgctl_install
short_description: Install rgctl binary on local machines
description:
  - Downloads and installs rgctl from GitHub releases.
  - Idempotent - skips install if correct version already present.
  - For AAP use the execution-environment image instead of this module.
options:
  version:
    description:
      - Version to install. Use 'latest' to resolve at runtime.
      - Use 'skip-install' to skip installation (expects rgctl already in PATH via EE).
    type: str
    default: latest
  install_path:
    description: Directory to install the binary into.
    type: str
    default: /usr/local/bin
  arch:
    description: CPU architecture. Defaults to auto-detected.
    type: str
    default: x86_64
"""

RETURN = r"""
changed:
  description: Whether the binary was installed or upgraded.
  type: bool
rgctl_version_installed:
  description: The installed version string.
  type: str
msg:
  description: Human-readable result message.
  type: str
"""

import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
import urllib.request

from ansible.module_utils.basic import AnsibleModule

GITHUB_API = "https://api.github.com/repos/rgctl/rgctl/releases"
DOWNLOAD_BASE = "https://github.com/rgctl/rgctl/releases/download"


def _resolve_latest_version():
    with urllib.request.urlopen(f"{GITHUB_API}/latest", timeout=15) as resp:
        data = json.loads(resp.read())
    return data["tag_name"].lstrip("v")


def _build_download_url(version, arch):
    if arch == "aarch64":
        # Only macOS aarch64 is released; Linux aarch64 not available
        raise ValueError("rgctl does not publish Linux aarch64 binaries. Only x86_64 is supported on Linux.")
    return (
        f"{DOWNLOAD_BASE}/v{version}/rgctl-{version}-x86_64-unknown-linux-gnu.tar.gz",
        f"{DOWNLOAD_BASE}/v{version}/SHA256SUMS.txt",
    )


def _download_and_install(version, install_path, arch):
    tarball_url, sums_url = _build_download_url(version, arch)

    with tempfile.TemporaryDirectory() as tmpdir:
        tarball_path = os.path.join(tmpdir, "rgctl.tar.gz")
        sums_path = os.path.join(tmpdir, "SHA256SUMS.txt")

        urllib.request.urlretrieve(tarball_url, tarball_path)
        urllib.request.urlretrieve(sums_url, sums_path)

        # Verify SHA256
        sha256 = hashlib.sha256()
        with open(tarball_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        digest = sha256.hexdigest()
        tarball_name = os.path.basename(tarball_url)
        with open(sums_path) as f:
            for line in f:
                expected_hash, name = line.strip().split(None, 1)
                if name.strip() == tarball_name:
                    if digest != expected_hash:
                        raise RuntimeError(f"SHA256 mismatch for {tarball_name}: expected {expected_hash}, got {digest}")
                    break
            else:
                raise RuntimeError(f"Could not find {tarball_name} in SHA256SUMS.txt")

        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(tmpdir)

        binary_src = os.path.join(tmpdir, "rgctl")
        binary_dst = os.path.join(install_path, "rgctl")
        os.makedirs(install_path, exist_ok=True)
        with open(binary_src, "rb") as src, open(binary_dst, "wb") as dst:
            dst.write(src.read())
        os.chmod(binary_dst, 0o755)

    return version


def _get_installed_version(rgctl_bin="rgctl"):
    result = subprocess.run(
        [rgctl_bin, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return None
    # Output: "rgctl 0.4.26" or "rgctl v0.4.26"
    parts = result.stdout.strip().split()
    if len(parts) >= 2:
        return parts[-1].lstrip("v")
    return None


def run_module(module):
    version = module.params["version"]
    install_path = module.params["install_path"]
    arch = module.params["arch"]

    rgctl_bin = os.path.join(install_path, "rgctl")

    # Resolve 'latest' to actual version
    if version == "latest":
        try:
            version = _resolve_latest_version()
        except Exception as e:
            module.fail_json(msg=f"Could not resolve latest rgctl version: {e}")

    try:
        installed = _get_installed_version(rgctl_bin)
    except FileNotFoundError:
        installed = None
    except subprocess.TimeoutExpired:
        installed = None

    if version == "skip-install":
        if installed is None:
            module.fail_json(
                msg=(
                    "rgctl not found in PATH. For AAP, build and deploy the "
                    "execution-environment image from the execution-environment/ "
                    "directory. For local machines, set version to a real version number."
                )
            )
        module.exit_json(changed=False, rgctl_version_installed=installed, msg=f"rgctl {installed} already present")

    if installed == version:
        module.exit_json(
            changed=False,
            rgctl_version_installed=installed,
            msg=f"rgctl {version} already installed",
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            rgctl_version_installed=version,
            msg=f"Would install rgctl {version}",
        )

    try:
        installed_version = _download_and_install(version, install_path, arch)
    except Exception as e:
        module.fail_json(msg=f"Failed to install rgctl {version}: {e}")

    module.exit_json(
        changed=True,
        rgctl_version_installed=installed_version,
        msg=f"rgctl {installed_version} installed to {install_path}",
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            version=dict(type="str", default="latest"),
            install_path=dict(type="str", default="/usr/local/bin"),
            arch=dict(type="str", default="x86_64"),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == "__main__":
    main()
