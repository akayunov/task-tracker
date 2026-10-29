"""E2E: health и корневой редирект."""

import pytest

from tests.e2e.resources.health import Health

pytestmark = pytest.mark.e2e


def test_health_and_readiness():
    Health().check()
    Health().ready()


def test_root_redirects_to_docs():
    Health().root()
