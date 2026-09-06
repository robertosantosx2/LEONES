#!/usr/bin/env python3
"""Historical V1 selector-to-A01 tests retained for audit purposes."""
from __future__ import annotations

import pytest

# RC3 replaces the legacy runtime-selection.v1 selector path with Hermes plus
# the Leo001-Leo010 task benchmark loop. These V1 tests are no longer a valid
# assertion of the canonical RC3 architecture.
pytest.skip(
    "legacy V1 selector-to-A01 path is superseded by RC3 Hermes/Leo benchmark",
    allow_module_level=True,
)
