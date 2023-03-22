import pytest

from tr_rm import config


@pytest.fixture(autouse=True, scope="session")
def setup_config():
    config.override(
        DATABASE_URL="sqlite:///:memory:",
        # DATABASE_URL="sqlite:///test.db",
        LOG_LEVEL="DEBUG",
    )
    yield
