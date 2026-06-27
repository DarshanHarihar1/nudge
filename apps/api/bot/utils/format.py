from decimal import Decimal


def format_amount(amount: float | str | Decimal, currency: str = "INR") -> str:
    num = float(amount)
    if currency == "INR":
        return f"₹{int(num):,}"
    return f"{num:,.2f} {currency}"
