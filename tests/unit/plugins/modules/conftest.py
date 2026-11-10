import sys
import pathlib
import types

# Add plugins/modules to path so test files can import modules directly
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent / "plugins" / "modules"))

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
