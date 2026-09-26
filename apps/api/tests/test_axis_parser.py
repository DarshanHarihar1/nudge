from utils.email_parser import (
    AXIS_SENDER, IGNORE, UBI_SENDER, parse_axis_cc_email, parse_bank_email,
)
from tests.test_email_parser import REAL_CAPTURED_EMAIL


def axis_spend(amount="INR 2000", merchant="PLAY ARENA", when="20-09-2026, 14:34:30"):
    # Shape of a real alert (card digits masked); values sit in their own cells.
    return (
        "<table><tr><td>Dear Darshan Harihar,</td></tr>"
        "<tr><td>Here's the summary of your Axis Bank Credit Card Transaction:</td></tr>"
        f"<tr><td>Transaction Amount:</td><td>{amount}</td></tr>"
        f"<tr><td>Merchant Name:</td><td>{merchant}</td></tr>"
        "<tr><td>Axis Bank Credit Card No.</td><td>XX0000</td></tr>"
        f"<tr><td>Date &amp; Time:</td><td>{when} IST</td></tr>"
        "<tr><td>Available Limit*:</td><td>INR 107398.19</td></tr></table>"
    )


def test_inr_spend():
    p = parse_axis_cc_email(axis_spend())
    assert (p.payee, p.amount, p.currency, p.status) == ("PLAY ARENA", 2000.0, "INR", "Success")
    assert p.occurred_at == "20-09-2026 14:34:30"
    assert p.rrn == "axis:XX0000:20-09-2026 14:34:30:INR:2000"


def test_usd_spend_and_odd_merchant_names():
    p = parse_axis_cc_email(axis_spend("USD 23.6", "ANTHROPIC*", "08-09-2026, 18:08:46"))
    assert (p.payee, p.amount, p.currency) == ("ANTHROPIC*", 23.6, "USD")
    p = parse_axis_cc_email(axis_spend("INR 649", "CURSOR, AI"))
    assert p.payee == "CURSOR, AI"


def test_non_transaction_mail_is_none():
    assert parse_axis_cc_email("<p>Here's the summary of your upcoming AutoPay transaction:</p>") is None


def test_dispatch_by_sender_and_subject():
    assert parse_bank_email(f"Axis Bank Alerts <{AXIS_SENDER}>", "INR 2000 spent on credit card no. XX0000", axis_spend()).payee == "PLAY ARENA"
    for subject in ["Upcoming AutoPay txn. reminder", "AutoPay for Hotstar: ACTIVATED",
                    "USD 1 txn. reversed at NORTHFLANK", "We value your feedback"]:
        assert parse_bank_email(AXIS_SENDER, subject, "<p>whatever</p>") is IGNORE
    assert parse_bank_email(UBI_SENDER, "DEBIT TRANSACTION ALERT", REAL_CAPTURED_EMAIL).payee == "ZOMATO"
