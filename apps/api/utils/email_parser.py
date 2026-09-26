"""
Deterministic parsers for bank alert emails — fixed templates, so regex,
not an LLM call:
- Union Bank of India "DEBIT TRANSACTION ALERT" (UPI debits): a numbered
  "Transaction Details" block, confirmed identical across live samples.
- Axis Bank credit card "INR/USD <amt> spent on credit card" alerts.
"""
import html
import re
from dataclasses import dataclass
from typing import Optional

_BLOCK_RE = re.compile(
    r"Transaction Details.*?(?=If you have not initiated|Alert Section|$)",
    re.S | re.I,
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


UBI_SENDER = "noreplyubi-txn@ubi.bank.in"
AXIS_SENDER = "alerts@axis.bank.in"
BANK_SENDERS = (UBI_SENDER, AXIS_SENDER)

# Returned for bank mail that isn't a spend (AutoPay notices, reversals,
# feedback) — skipped without the "couldn't parse" warning.
IGNORE = object()

_AXIS_AMOUNT_RE = re.compile(r"Transaction Amount:\s*([A-Z]{3})\s*([\d,]+(?:\.\d+)?)")
_AXIS_MERCHANT_RE = re.compile(r"Merchant Name:\s*(.+?)\s*Axis Bank Credit Card No\.")
_AXIS_CARD_RE = re.compile(r"Credit Card No\.\s*(XX\d{4})")
_AXIS_WHEN_RE = re.compile(r"Date & Time:\s*(\d{2}-\d{2}-\d{4}),\s*(\d{2}:\d{2}:\d{2})")


def _plain_text(markup: str) -> str:
    text = re.sub(r"(?is)<(style|script).*?</\1>", " ", markup)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text)).split())


def parse_axis_cc_email(markup: str) -> Optional[ParsedDebitEmail]:
    text = _plain_text(markup)
    if "summary of your Axis Bank Credit Card Transaction" not in text:
        return None
    amount = _AXIS_AMOUNT_RE.search(text)
    merchant = _AXIS_MERCHANT_RE.search(text)
    card = _AXIS_CARD_RE.search(text)
    when = _AXIS_WHEN_RE.search(text)
    if not (amount and merchant and card and when):
        return None
    currency, raw_amount = amount.group(1), amount.group(2).replace(",", "")
    occurred_at = f"{when.group(1)} {when.group(2)}"
    return ParsedDebitEmail(
        payee=merchant.group(1),
        amount=float(raw_amount),
        currency=currency,
        channel="CREDIT_CARD",
        # Axis alerts carry no transaction ID; card + timestamp + amount is
        # stable across redeliveries of the same alert.
        rrn=f"axis:{card.group(1)}:{occurred_at}:{currency}:{raw_amount}",
        status="Success",
        occurred_at=occurred_at,
    )


def parse_bank_email(sender: str, subject: str, markup: str):
    """ParsedDebitEmail, None (a spend alert we couldn't read), or IGNORE."""
    if AXIS_SENDER in sender:
        # ponytail: reversals are skipped for now; refund matching is the
        # next step after this plan.
        if "spent on credit card" not in subject.lower():
            return IGNORE
        return parse_axis_cc_email(markup)
    return parse_ubi_debit_email(markup)
