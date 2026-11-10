import importlib.util
import sys
import pathlib
import types

# Add plugins/modules and plugins/ to path so test files can import modules directly
_plugins = pathlib.Path(__file__).parent.parent.parent.parent.parent / "plugins"
sys.path.insert(0, str(_plugins / "modules"))
sys.path.insert(0, str(_plugins))

# Stub ansible.module_utils so imports work without ansible-core installed in test env
ansible_stub = types.ModuleType("ansible")
mu_stub = types.ModuleType("ansible.module_utils")
basic_stub = types.ModuleType("ansible.module_utils.basic")


class FakeAnsibleModule:
    def __init__(self, argument_spec, **kwargs):
        self.params = {k: v.get("default") for k, v in argument_spec.items()}
        self.check_mode = False

    def exit_json(self, **kwargs):
        raise SystemExit(kwargs)

    def fail_json(self, **kwargs):
        raise RuntimeError(kwargs.get("msg", str(kwargs)))


basic_stub.AnsibleModule = FakeAnsibleModule
ansible_stub.module_utils = mu_stub
mu_stub.basic = basic_stub
sys.modules.setdefault("ansible", ansible_stub)
sys.modules.setdefault("ansible.module_utils", mu_stub)
sys.modules.setdefault("ansible.module_utils.basic", basic_stub)

# Load real rgctl_common from the filesystem and register as ansible.module_utils.rgctl_common
_common_path = _plugins / "module_utils" / "rgctl_common.py"
_spec = importlib.util.spec_from_file_location("ansible.module_utils.rgctl_common", _common_path)
_common_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_common_mod)
sys.modules["ansible.module_utils.rgctl_common"] = _common_mod
mu_stub.rgctl_common = _common_mod

# Also register under the collection-qualified path used in production imports
_coll_path = "ansible_collections.rgctl.rgctl.plugins.module_utils.rgctl_common"
sys.modules[_coll_path] = _common_mod
