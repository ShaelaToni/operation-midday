"""Presentation filters for the Noon Report - money and gap formatting. Formatting is a template
concern (the pure builder leaves values unformatted); these render them for display."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def money(value):
    """Format a Decimal/number as US currency: $1,234.56. Blank on None/invalid."""
    if value is None:
        return ""
    try:
        d = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return ""
    return f"${d:,.2f}"


@register.filter
def gap(value):
    """Quantize the gap multiple to two places for display: 2.27. Safe on None/zero."""
    if value is None:
        return "0.00"
    try:
        return f"{Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"
    except (InvalidOperation, TypeError, ValueError):
        return "0.00"
