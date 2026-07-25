import pytest

from app.config import Settings
from app.graph import build_deps


@pytest.fixture
def settings() -> Settings:
    return Settings(llm_provider="fake", database_url=None, redis_url=None)


@pytest.fixture
def deps(settings):
    # Memory disabled: fully offline, no DB required.
    return build_deps(settings, enable_memory=False)
