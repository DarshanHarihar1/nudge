from utils.email_parser import parse_ubi_debit_email

SUCCESS_EMAIL = """
<div>
Dear <strong>DARSHAN HARIHAR</strong>,<br><br>
Your fund transfer request through <strong>UPI</strong> has been processed successfully.<br><br>
<div>
  <div>Transaction Details</div>
  1. Payee Name :   ZOMATO<br>
  2. Amount : Rs. 97.84<br>
  3. Channel : UPI<br>
  4. Transaction ID/RRN : 561297249109<br>
  5. Transaction Status : Success<br>
  6. Transaction Date and Time : 16-09-2026 22:11:19<br>
  7. Debit Account Number : *4200
</div>
<br>
<div>
  If you have not initiated this transaction, please report it immediately
</div>
</div>
"""

FAILED_EMAIL = SUCCESS_EMAIL.replace("Success", "Failed")

COMMA_AMOUNT_EMAIL = SUCCESS_EMAIL.replace("Rs. 97.84", "Rs. 1,234.50")

NON_TRANSACTION_EMAIL = """
<div>Your monthly e-statement is now available. Log in to download it.</div>
"""


def test_parses_success_email():
    result = parse_ubi_debit_email(SUCCESS_EMAIL)
    assert result is not None
    assert result.payee == "ZOMATO"
    assert result.amount == 97.84
    assert result.currency == "INR"
    assert result.channel == "UPI"
    assert result.rrn == "561297249109"
    assert result.status == "Success"
    assert result.occurred_at == "16-09-2026 22:11:19"


def test_parses_failed_status():
    result = parse_ubi_debit_email(FAILED_EMAIL)
    assert result is not None
    assert result.status == "Failed"


def test_parses_comma_separated_amount():
    result = parse_ubi_debit_email(COMMA_AMOUNT_EMAIL)
    assert result is not None
    assert result.amount == 1234.50


def test_returns_none_for_non_transaction_email():
    assert parse_ubi_debit_email(NON_TRANSACTION_EMAIL) is None


def test_returns_none_for_empty_string():
    assert parse_ubi_debit_email("") is None
