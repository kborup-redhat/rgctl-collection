"""Shared helpers for rgctl Ansible modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json
import subprocess


EE_HINT = (
    "rgctl not found in PATH. For AAP, build and deploy the "
    "execution-environment image. For local machines, use "
    "rgctl.rgctl.rgctl_install first."
)


def run_rgctl(args, path, rgctl_bin, timeout):
    """Run an rgctl command and return (returncode, stdout, stderr).

    args     — list of arguments after the binary name, e.g. ["find", "Owner", "-f", "json"]
    path     — repo root passed as -r
    rgctl_bin — binary path/name
    timeout  — seconds

    Raises RuntimeError on FileNotFoundError or TimeoutExpired.
    """
    cmd = [rgctl_bin, "-r", path, "-f", "json"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError(EE_HINT)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"rgctl {args[0]} timed out after {timeout}s")
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def parse_json(stdout, cmd_name):
    """Parse JSON stdout; raise RuntimeError on failure."""
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"rgctl {cmd_name} returned non-JSON output: {stdout[:200]}")


def check_error_envelope(data, cmd_name):
    """Raise RuntimeError if the parsed data contains an rgctl error envelope."""
    if isinstance(data, dict) and data.get("ok") is False:
        code = data.get("error_code", data.get("error", "unknown"))
        msg = data.get("message", "")
        recovery = data.get("recovery_command", "")
        detail = f": {msg}" if msg else ""
        hint = f" — try: {recovery}" if recovery else ""
        raise RuntimeError(f"rgctl {cmd_name} error ({code}){detail}{hint}")
