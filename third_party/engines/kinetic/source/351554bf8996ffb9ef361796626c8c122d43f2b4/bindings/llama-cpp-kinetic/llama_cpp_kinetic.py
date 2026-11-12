"""Makes `import llama_cpp` load `kinetic.llama_cpp`.

It runs at interpreter start from llama_cpp_kinetic.pth. An installed
llama-cpp-python is shadowed, not touched: uninstalling this package brings
it back.
"""

import importlib
import importlib.abc
import importlib.util
import sys


class _Alias(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, name, path=None, target=None):
        if name != "llama_cpp":
            return None
        return importlib.util.spec_from_loader(name, self)

    def create_module(self, spec):
        return importlib.import_module("kinetic.llama_cpp")

    def exec_module(self, module):
        pass


if not any(isinstance(f, _Alias) for f in sys.meta_path):
    sys.meta_path.insert(0, _Alias())
