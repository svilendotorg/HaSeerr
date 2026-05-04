"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "seerr"


@pytest.fixture
def fixture():
    """Load a Seerr fixture JSON by name (without .json suffix)."""

    def _load(name: str):
        return json.loads((FIXTURE_DIR / f"{name}.json").read_text())

    return _load


@pytest.fixture
def seerr_url() -> str:
    return "http://test.local:5055"


@pytest.fixture
def seerr_api_key() -> str:
    return "test-api-key"
