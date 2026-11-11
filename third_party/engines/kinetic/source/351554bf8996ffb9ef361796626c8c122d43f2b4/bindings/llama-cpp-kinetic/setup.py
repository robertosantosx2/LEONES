import os

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithPth(build_py):
    """Puts the .pth file at the top of site-packages, where Python runs it."""

    def run(self):
        super().run()
        name = "llama_cpp_kinetic.pth"
        self.copy_file(name, os.path.join(self.build_lib, name))


setup(cmdclass={"build_py": BuildWithPth})
