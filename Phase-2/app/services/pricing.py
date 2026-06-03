"""
Dynamic pricing — the project's unique feature.

Rules (from DECISIONS.md):
  occupancy < 0.50            -> tier 'low',  multiplier 1.00
  0.50 <= occupancy <= 0.80   -> tier 'mid',  multiplier 1.15
  occupancy > 0.80            -> tier 'high', multiplier 1.25

VIP seats get an additional 1.5x multiplier on top of the tier multiplier.
Prices are calculated at query time, never stored — except `price_at_booking`,
which is frozen onto the booking row at confirmation time.
"""

from decimal import Decimal, ROUND_HALF_UP


def pricing_tier(occupancy_rate: float) -> tuple[str, Decimal]:
    """Return (tier_name, multiplier) for the given occupancy rate (0.0..1.0)."""
    if occupancy_rate < 0.5:
        return "low", Decimal("1.00")
    if occupancy_rate <= 0.8:
        return "mid", Decimal("1.15")
    return "high", Decimal("1.25")


def calculate_seat_price(base_price: Decimal, occupancy_rate: float, seat_type: str) -> Decimal:
    """Compute the live price of a single seat. Always rounded to 2 decimal places."""
    _, multiplier = pricing_tier(occupancy_rate)
    price = Decimal(base_price) * multiplier
    if seat_type == "vip":
        price = price * Decimal("1.5")
    return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
