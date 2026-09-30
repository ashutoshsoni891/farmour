import pytest

from app.core.phone import normalise_indian_phone


@pytest.mark.parametrize(
    "raw",
    ["9876543210", "+91 98765 43210", "09876543210", "91-9876543210"],
)
def test_valid_numbers_normalise(raw: str) -> None:
    assert normalise_indian_phone(raw) == "+919876543210"


@pytest.mark.parametrize("raw", ["12345", "5876543210", "+1 415 555 0100", ""])
def test_invalid_numbers_rejected(raw: str) -> None:
    with pytest.raises(ValueError, match="invalid"):
        normalise_indian_phone(raw)
