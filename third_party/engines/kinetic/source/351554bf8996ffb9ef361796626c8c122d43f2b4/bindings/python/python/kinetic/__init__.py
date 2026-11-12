"""Kinetic: open engine for running AI locally.

`kinetic.Model` loads a .gguf or .ktc file; `kinetic.llama_cpp` offers the
`Llama` class of llama-cpp-python on top of it.
"""

from ._kinetic import Model, TextStream, __version__

__all__ = ["Model", "TextStream", "__version__"]
