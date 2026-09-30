"""Phone number normalisation (Indian mobiles, E.164)."""

import re

_NON_DIGITS = re.compile(r"\D")


def normalise_indian_phone(value: str) -> str:
    """Accept 10-digit Indian mobiles with or without a +91 or 0 prefix; return E.164."""
    digits = _NON_DIGITS.sub("", value)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != 10 or digits[0] not in "6789":
        raise ValueError("invalid Indian mobile number")
    return "+91" + digits
