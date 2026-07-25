"""Shared test fixtures."""

import pytest


@pytest.fixture
def mock_ebird_api_key() -> str:
    return "test-api-key"
