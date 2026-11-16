from decimal import Decimal, ROUND_HALF_UP

TWOPLACES = Decimal("0.01")


def money(value) -> float:
    amount = Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    return float(amount)


def line_total(quantity: int, unit_price: float) -> float:
    total = Decimal(quantity) * Decimal(str(unit_price))
    return float(total.quantize(TWOPLACES, rounding=ROUND_HALF_UP))
