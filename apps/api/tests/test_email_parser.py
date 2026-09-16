from utils.email_parser import parse_ubi_debit_email

REAL_CAPTURED_EMAIL = """<div style="margin:0;padding:20px;background:#f4f7fb;font-family:Arial,Helvetica,sans-serif;">

  <div style="max-width:650px;margin:auto;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #dce3ec;">

    <!-- Body -->
    <div style="padding:25px;color:#333333;font-size:14px;line-height:1.7;">

      Dear <strong>DARSHAN HARIHAR</strong>,<br><br>

      Greetings!<br><br>

      Your fund transfer request through <strong>UPI</strong> has been processed successfully.<br><br>

      <!-- Transaction Details -->
      <div style="background:#f8fbff;border:1px solid #d7e6fa;border-radius:8px;padding:18px;">

        <div style="font-size:18px;font-weight:bold;color:#004b8d;margin-bottom:12px;">
          Transaction Details
        </div>

        1. Payee Name :   ZOMATO<br>
        2. Amount : Rs. 97.84<br>
        3. Channel : UPI<br>
        4. Transaction ID/RRN : 561297249109<br>
        5. Transaction Status : Success<br>
        6. Transaction Date and Time : 16-09-2026 22:11:19<br>
        7. Debit Account Number : *4200

      </div>

      <br>

      <!-- Alert Section -->
      <div style="background:#fff4f4;border-left:5px solid #d71920;padding:15px;border-radius:4px;">

        <span style="font-size:16px;font-weight:bold;color:#d71920;">
          If you have not initiated this transaction, please report it immediately by way of:
        </span>

        <br><br>

        SMS UEBT to 8879365472<br><br>

        OR <b>SMS "BLOCK"&#60;SPACE&#62;&#60;LAST FOUR DIGIT A/C NO.&#62; TO 8879365472</b>

        OR Call our Toll Free Numbers: 1800 8333 / 1800 2333 / 1800 8331 / 1800 8332<br><br>

        NRI Dedicated Number: 022 44546567 / Cyber Crime LEA Support Desk: 022 44546565<br><br>

        OR mail to cyber.incidents [@] unionbankofindia [dot] bank [dot] in with Subject "Unauthorized Transaction Complaint"<br><br>

        OR visit: unauthdigitxn [dot] unionbankportal [dot] bank [dot] in/<br><br>

        OR visit your nearest branch

      </div>

      <br>

      <!-- Safe Banking Tips -->
      <div style="background:#fffbea;border:1px solid #f2df9f;border-radius:8px;padding:18px;">

        <div style="font-size:18px;font-weight:bold;color:#b8860b;margin-bottom:10px;">
          Safe Banking Tips
        </div>

        • Always download Union-Ease Mobile App from the official Play Store/App Store only.<br>
        • To report any cybercrime, dial 1930 or visit www [dot] cybercrime [dot] gov [dot] in.<br>
        • To report any suspicious SMS, phone calls, or WhatsApp messages, visit https://sancharsaathi [dot] gov [dot] in/sfc/.<br>
        • Never share your Card Number, CVV, PIN, OTP, Internet Banking UserID, Password or URN with anyone, even if the caller claims to be a Bank employee. Sharing these details can lead to unauthorised access to your account.<br>
        • Fraudsters under the pretext of bank services/ any other public utility services are sending scamming links/ contact details/QR Codes/Spurious Calls /False Notifications/Letters through SMS/WhatsApp message/ Email/ Fake Advertisements on online search engines to make a unauthorised debit to your bank account. Be aware of such fraudsters and verify the genuineness of the sender before responding. Kindly contact the bank/bank official in case of any further guidance.

      </div>

      <br>

      

      Regards,<br>
      <strong>Union Bank of India</strong>

    </div>

  
     <p><img src="https://unionbankonline.bank.in/images/logo.png" alt="Bank logo" width="300" style="display: block; margin-left: auto; margin-right: auto;" /></p>
  </div>

</div>
<p>&nbsp;<br></p>
"""

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


def test_parses_real_captured_email():
    result = parse_ubi_debit_email(REAL_CAPTURED_EMAIL)
    assert result is not None
    assert result.payee == "ZOMATO"
    assert result.amount == 97.84
    assert result.currency == "INR"
    assert result.channel == "UPI"
    assert result.rrn == "561297249109"
    assert result.status == "Success"
    assert result.occurred_at == "16-09-2026 22:11:19"
