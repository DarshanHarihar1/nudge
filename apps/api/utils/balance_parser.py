import re


def parse_balance(text: str) -> float | None:
    """
    Parse a balance amount from freeform text.
    Handles: 48200  48,200  ₹48200  ₹48,200  48k  48.5k
    Returns None if text cannot be parsed as a number.
    """
    t = text.strip()
    # Strip currency symbols, rupee sign, spaces, commas
    t = re.sub(r"[₹$€£\s,]", "", t)

    # Match 'k' suffix (case-insensitive)
    m = re.fullmatch(r"(\d+(?:\.\d+)?)k", t, re.IGNORECASE)
    if m:
        return float(m.group(1)) * 1_000

    # Plain integer or decimal
    m = re.fullmatch(r"\d+(?:\.\d+)?", t)
    if m:
        return float(m.group(0))

    return None
