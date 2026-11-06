import os
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from app.services.settings_service import get_settings_service


@pytest.fixture(autouse=True)
def reset_settings_for_tests():
    service = get_settings_service()
    service.reset_to_defaults()
    yield
    service.reset_to_defaults()

