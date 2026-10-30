"""Spread invoice amounts over hourly cost statistics."""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from datetime import tzinfo
from typing import Dict, List, Tuple

# Invoice amounts that grow with the volume consumed. Everything else in the
# invoice total (service fee, waste taxes, regularizations...) is fixed.
VOLUME_AMOUNT_FIELDS = (
    "consumptionAmount",
    "waterCanonAmount",
    "clavegueramAmount",
    "clavegueramSoreaAmount",
    "clavegueramPortAmount",
)

INVOICE_DATE_FORMAT = "%d-%m-%Y"


def invoice_period(invoice: Dict, tz: tzinfo) -> Tuple[datetime, datetime]:
    """Return the invoice billing period as [start, end) local midnights."""
    start = datetime.strptime(invoice["startDate"], INVOICE_DATE_FORMAT)
    end = datetime.strptime(invoice["endDate"], INVOICE_DATE_FORMAT)
    return start.replace(tzinfo=tz), end.replace(tzinfo=tz)


def split_invoice_amount(invoice: Dict) -> Tuple[float, float]:
    """Split the invoice total into (fixed, variable) amounts.

    VAT only applies to the water service (fee + consumption), so its
    share on the consumption is counted as variable.
    """
    total = invoice.get("amount") or 0.0
    variable = sum(invoice.get(field) or 0.0 for field in VOLUME_AMOUNT_FIELDS)

    water_service = invoice.get("waterServiceAmount") or 0.0
    if water_service:
        consumption = invoice.get("consumptionAmount") or 0.0
        variable += (invoice.get("ivaAmount") or 0.0) * consumption / water_service

    return total - variable, variable


def hourly_costs(
    start: datetime,
    end: datetime,
    fixed: float,
    variable: float,
    hourly_consumption: Dict[datetime, float],
) -> List[Tuple[datetime, float]]:
    """Spread an invoice over the hours in [start, end).

    The fixed amount is spread evenly. The variable amount follows the
    hourly consumption on the hours that have consumption data, and is
    spread evenly over the hours without it, so a period only partly
    imported doesn't pile its whole variable amount on a few days.
    Returns sorted (UTC hour start, cost) tuples.
    """
    # Step in UTC so DST days get their real 23 or 25 hours
    hours = []
    hour = start.astimezone(timezone.utc)
    while hour < end:
        hours.append(hour)
        hour += timedelta(hours=1)
    if not hours:
        return []

    fixed_per_hour = fixed / len(hours)
    variable_per_hour = variable / len(hours)
    covered = [h for h in hours if h in hourly_consumption]
    covered_consumption = sum(hourly_consumption[h] for h in covered)
    covered_variable = variable_per_hour * len(covered)

    result = []
    for hour in hours:
        if covered_consumption > 0 and hour in hourly_consumption:
            cost = covered_variable * hourly_consumption[hour] / covered_consumption
        else:
            cost = variable_per_hour
        result.append((hour, fixed_per_hour + cost))
    return result
