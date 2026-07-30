"""Test setup that isolates Home Assistant-independent modules."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

# Importing a Home Assistant integration normally executes its package
# initializer. Fast client/helper tests deliberately isolate modules that have
# no Home Assistant dependency, so contributors do not need a full HA install.
package = ModuleType("custom_components.v2c_trydan")
package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "v2c_trydan")]
sys.modules["custom_components.v2c_trydan"] = package
