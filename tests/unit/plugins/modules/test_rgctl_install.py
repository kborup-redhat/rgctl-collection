import pytest
from unittest.mock import patch, MagicMock


def _run(params, check_mode=False):
    import rgctl_install as m
    mod = m.AnsibleModule.__new__(m.AnsibleModule)
    mod.params = params
    mod.check_mode = check_mode
    with pytest.raises(SystemExit) as exc:
        m.run_module(mod)
    return exc.value.args[0]


def _params(**overrides):
    base = {"version": "0.4.26", "install_path": "/usr/local/bin", "arch": "x86_64"}
    base.update(overrides)
    return base


def test_already_installed_correct_version():
    with patch("subprocess.run") as sp:
        sp.return_value = MagicMock(returncode=0, stdout="rgctl 0.4.26\n")
        result = _run(_params())
    assert result["changed"] is False
    assert result["rgctl_version_installed"] == "0.4.26"


def test_rgctl_not_in_path_triggers_download():
    with patch("subprocess.run") as sp, patch("rgctl_install._download_and_install") as dl:
        sp.side_effect = FileNotFoundError
        dl.return_value = "0.4.26"
        result = _run(_params())
    assert result["changed"] is True
    dl.assert_called_once()


def test_wrong_version_triggers_upgrade():
    with patch("subprocess.run") as sp, patch("rgctl_install._download_and_install") as dl:
        sp.return_value = MagicMock(returncode=0, stdout="rgctl 0.4.0\n")
        dl.return_value = "0.4.26"
        result = _run(_params())
    assert result["changed"] is True


def test_check_mode_no_install():
    with patch("subprocess.run") as sp, patch("rgctl_install._download_and_install") as dl:
        sp.side_effect = FileNotFoundError
        result = _run(_params(), check_mode=True)
    dl.assert_not_called()
    assert result["changed"] is True


def test_skip_install_version_in_aap_gives_clear_message():
    with patch("subprocess.run") as sp:
        sp.side_effect = FileNotFoundError
        with pytest.raises(RuntimeError) as exc:
            _run(_params(version="skip-install"))
    assert "execution-environment" in str(exc.value).lower()
