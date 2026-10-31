"""Real HA fixtures live in the separately pinned Linux test environment."""

import pytest


@pytest.fixture(autouse=True)
def enable_integration(enable_custom_integrations):
    """Explicitly permit loading the repository's custom integration in tests."""
