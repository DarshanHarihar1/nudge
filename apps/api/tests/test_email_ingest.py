import pytest

from services.email_ingest import needs_recategorize


@pytest.mark.parametrize("confidence,expected", [
    (0.0, True),
    (0.59, True),
    (0.6, False),
    (0.61, False),
    (1.0, False),
])
def test_needs_recategorize(confidence, expected):
    assert needs_recategorize(confidence) is expected
