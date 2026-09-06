"""Historical RC2 hardware-profile contracts.

RC3 deliberately removes LLMFit/FitLLM from the active route. The legacy
provenance assertion below therefore no longer describes the canonical system.
"""

import pytest

pytest.skip(
    "RC2 hardware-profile contract is historical; LLMFit/FitLLM is outside RC3",
    allow_module_level=True,
)
