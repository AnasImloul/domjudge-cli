"""Pytest configuration and fixtures for DOMjudge CLI tests."""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def mock_secrets_dir(temp_dir):
    """Create a temporary secrets directory."""
    secrets_dir = temp_dir / ".dom"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    return secrets_dir


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "infra": {
            "port": 8080,
            "judges": 2,
        },
        "contests": [
            {
                "name": "Test Contest",
                "shortname": "TEST2025",
                "start_time": "2025-06-01T10:00:00+00:00",
                "duration": "5:00:00.000",
                "penalty_time": 20,
                "allow_submit": True,
            }
        ],
    }
