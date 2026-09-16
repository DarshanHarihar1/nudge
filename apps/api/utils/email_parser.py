"""
Deterministic parser for Union Bank of India's "DEBIT TRANSACTION ALERT"
emails (sender: noreplyubi-txn@ubi.bank.in). The bank's template embeds a
fixed numbered "Transaction Details" block — confirmed identical across
live samples, so this is regex, not an LLM call.
"""
import re
from dataclasses import dataclass
from typing import Optional

_BLOCK_RE = re.compile(
    r"Transaction Details.*?(?=If you have not initiated|Alert Section|$)",
    re.S,
)
_FIELD_RE = re.compile(r"\d+\.\s*([^:<]+?)\s*:\s*([^<\n]+)")
_AMOUNT_RE = re.compile(r"([\d,]+\.?\d*)")


@dataclass
class ParsedDebitEmail:
    payee: str
    amount: float
    currency: str
    channel: str
    rrn: str
    status: str
    occurred_at: str


def parse_ubi_debit_email(html_text: str) -> Optional[ParsedDebitEmail]:
    """
    Extract payee/amount/status/etc. from the numbered "Transaction Details"
    block. Returns None if the block is missing or a required field is
    absent — e.g. a non-transactional email from the same sender
    (statement notice, promo) that doesn't match the debit-alert template.
    """
    block_match = _BLOCK_RE.search(html_text)
    if not block_match:
        return None

    fields = {
        key.strip().lower(): value.strip()
        for key, value in _FIELD_RE.findall(block_match.group(0))
    }

    payee = fields.get("payee name")
    amount_raw = fields.get("amount")
    rrn = fields.get("transaction id/rrn")
    status = fields.get("transaction status")

    if not all([payee, amount_raw, rrn, status]):
        return None

    amount_match = _AMOUNT_RE.search(amount_raw)
    if not amount_match:
        return None

    return ParsedDebitEmail(
        payee=payee,
        amount=float(amount_match.group(1).replace(",", "")),
        currency="INR",
        channel=fields.get("channel", ""),
        rrn=rrn,
        status=status,
        occurred_at=fields.get("transaction date and time", ""),
    )
