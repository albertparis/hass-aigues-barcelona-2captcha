"""Tests for spreading invoice amounts over hourly costs."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from custom_components.aigues_barcelona.costs import (
    hourly_costs,
    invoice_period,
    overlapping_periods,
    split_invoice_amount,
)
from custom_components.aigues_barcelona.sensor import ContratoAgua

MADRID = ZoneInfo("Europe/Madrid")

# Shape of a real invoice returned by /ofex-invoices-api/invoices
INVOICE = {
    "startDate": "09-07-2026",
    "endDate": "08-09-2026",
    "consumptionDays": 61,
    "consumptionVolume": 12,
    "amount": 102.11,
    "feeAmount": 32.74,
    "consumptionAmount": 9.87,
    "waterServiceAmount": 42.61,
    "waterCanonAmount": 8.28,
    "clavegueramAmount": 3.37,
    "clavegueramSoreaAmount": None,
    "clavegueramPortAmount": None,
    "tmtrAmount": 23.48,
    "trrAmount": 20.11,
    "ivaAmount": 4.26,
}


class TestInvoicePeriod:
    def test_period_matches_consumption_days(self):
        start, end = invoice_period(INVOICE, MADRID)

        assert start == datetime(2026, 7, 9, tzinfo=MADRID)
        assert end == datetime(2026, 9, 8, tzinfo=MADRID)
        assert (end - start).days == INVOICE["consumptionDays"]


class TestOverlappingPeriods:
    @staticmethod
    def _period(start_day, end_day):
        return (
            datetime(2026, 7, start_day, tzinfo=MADRID),
            datetime(2026, 7, end_day, tzinfo=MADRID),
        )

    def test_consecutive_periods_do_not_overlap(self):
        periods = [self._period(10, 20), self._period(1, 10)]

        assert overlapping_periods(periods) == []

    def test_detects_overlap_and_duplicate(self):
        first = self._period(1, 10)
        correction = self._period(1, 10)
        partial = self._period(5, 15)

        overlaps = overlapping_periods([partial, correction, first])

        assert overlaps == [(first, correction), (first, partial)]

    def test_period_inside_a_longer_one(self):
        long_period = self._period(1, 20)
        inside = self._period(5, 8)
        after = self._period(15, 25)

        overlaps = overlapping_periods([long_period, inside, after])

        assert overlaps == [(long_period, inside), (long_period, after)]


class TestSplitInvoiceAmount:
    def test_fixed_and_variable_add_up_to_total(self):
        fixed, variable = split_invoice_amount(INVOICE)

        assert fixed + variable == pytest.approx(INVOICE["amount"])

    def test_variable_includes_vat_share_of_consumption(self):
        _, variable = split_invoice_amount(INVOICE)

        vat_share = 4.26 * 9.87 / 42.61
        assert variable == pytest.approx(9.87 + 8.28 + 3.37 + vat_share)

    def test_missing_fields_count_as_zero(self):
        fixed, variable = split_invoice_amount({"amount": 50.0})

        assert (fixed, variable) == (50.0, 0.0)


class TestHourlyCosts:
    def test_total_cost_equals_invoice_amount(self):
        start = datetime(2026, 7, 9, tzinfo=MADRID)
        end = datetime(2026, 7, 11, tzinfo=MADRID)
        consumption = {
            datetime(2026, 7, 9, 6, tzinfo=timezone.utc): 0.02,
            datetime(2026, 7, 10, 19, tzinfo=timezone.utc): 0.06,
        }

        result = hourly_costs(start, end, 48.0, 8.0, consumption)

        assert len(result) == 48
        assert sum(cost for _, cost in result) == pytest.approx(56.0)

    def test_variable_follows_consumption(self):
        start = datetime(2026, 7, 9, tzinfo=MADRID)
        end = datetime(2026, 7, 10, tzinfo=MADRID)
        busy_hour = datetime(2026, 7, 9, 6, tzinfo=timezone.utc)
        other_hour = datetime(2026, 7, 9, 18, tzinfo=timezone.utc)
        idle_hour = datetime(2026, 7, 9, 12, tzinfo=timezone.utc)
        consumption = {
            start.astimezone(timezone.utc) + timedelta(hours=i): 0.0 for i in range(24)
        }
        consumption[busy_hour] = 0.03
        consumption[other_hour] = 0.01

        costs = dict(hourly_costs(start, end, 24.0, 4.0, consumption))

        assert costs[busy_hour] == pytest.approx(1.0 + 3.0)
        assert costs[other_hour] == pytest.approx(1.0 + 1.0)
        assert costs[idle_hour] == pytest.approx(1.0)

    def test_hours_without_data_get_an_even_share(self):
        # Consumption imported for the second day only
        start = datetime(2026, 7, 9, tzinfo=MADRID)
        end = datetime(2026, 7, 11, tzinfo=MADRID)
        second_day = datetime(2026, 7, 10, tzinfo=MADRID).astimezone(timezone.utc)
        consumption = {second_day + timedelta(hours=i): 0.0 for i in range(24)}
        consumption[second_day + timedelta(hours=8)] = 0.05

        result = hourly_costs(start, end, 0.0, 48.0, consumption)

        first_day_costs = [cost for _, cost in result[:24]]
        second_day_costs = [cost for _, cost in result[24:]]
        assert all(cost == pytest.approx(1.0) for cost in first_day_costs)
        assert sum(second_day_costs) == pytest.approx(24.0)
        assert second_day_costs[8] == pytest.approx(24.0)

    def test_variable_spread_evenly_without_consumption(self):
        start = datetime(2026, 7, 9, tzinfo=MADRID)
        end = datetime(2026, 7, 10, tzinfo=MADRID)

        result = hourly_costs(start, end, 12.0, 12.0, {})

        assert all(cost == pytest.approx(1.0) for _, cost in result)

    def test_hours_are_utc_and_cover_dst_change(self):
        # Clocks go back on 25-10-2026 in Spain: that day has 25 hours
        start = datetime(2026, 10, 25, tzinfo=MADRID)
        end = datetime(2026, 10, 26, tzinfo=MADRID)

        result = hourly_costs(start, end, 25.0, 0.0, {})

        assert len(result) == 25
        assert result[0][0] == datetime(2026, 10, 24, 22, tzinfo=timezone.utc)
        assert all(hour.tzinfo == timezone.utc for hour, _ in result)
        assert result[1][0] - result[0][0] == timedelta(hours=1)

    def test_empty_period(self):
        start = datetime(2026, 7, 9, tzinfo=MADRID)

        assert hourly_costs(start, start, 10.0, 5.0, {}) == []


class TestImportCostStatistics:
    """Tests for ContratoAgua._async_import_cost_statistics with the recorder
    mocked."""

    def _coordinator(self, invoices):
        async def run_in_executor(func, *args):
            return func(*args)

        coordinator = SimpleNamespace(
            contract="123",
            id="123",
            statistic_id="aigues_barcelona:123_consumption",
            cost_statistic_id="aigues_barcelona:123_cost",
            hass=SimpleNamespace(async_add_executor_job=run_in_executor),
            _api=SimpleNamespace(invoices=lambda *args: invoices),
            _get_hourly_consumption=AsyncMock(return_value={}),
        )
        coordinator._get_cost_statistics_metadata = lambda: "metadata"
        coordinator._warned_overlaps = set()
        coordinator._warn_overlapping_invoices = (
            lambda periods: ContratoAgua._warn_overlapping_invoices(
                coordinator, periods
            )
        )
        coordinator.run = lambda: ContratoAgua._async_import_cost_statistics(
            coordinator
        )
        return coordinator

    async def _run(self, invoices, last_stats):
        coordinator = self._coordinator(invoices)
        with (
            patch(
                "custom_components.aigues_barcelona.sensor.get_db_instance",
                return_value=coordinator.hass,
            ),
            patch(
                "custom_components.aigues_barcelona.sensor.get_last_statistics",
                return_value=last_stats,
            ),
            patch(
                "custom_components.aigues_barcelona.sensor.dt_util.get_default_time_zone",
                return_value=MADRID,
            ),
            patch(
                "custom_components.aigues_barcelona.sensor.async_add_external_statistics"
            ) as add_stats,
        ):
            await coordinator.run()
        return add_stats

    @staticmethod
    def _invoice(start, end, amount):
        return {"startDate": start, "endDate": end, "amount": amount}

    async def test_first_import_covers_all_invoices(self):
        invoices = [
            self._invoice("08-09-2026", "10-09-2026", 48.0),
            self._invoice("06-09-2026", "08-09-2026", 24.0),
        ]

        add_stats = await self._run(invoices, {})

        stats = add_stats.call_args.args[2]
        assert len(stats) == 96
        assert stats[0]["start"] == datetime(2026, 9, 5, 22, tzinfo=timezone.utc)
        assert stats[47]["sum"] == pytest.approx(24.0)
        assert stats[-1]["sum"] == pytest.approx(72.0)

    async def test_resumes_after_last_imported_cost(self):
        invoices = [
            self._invoice("06-09-2026", "08-09-2026", 24.0),
            self._invoice("08-09-2026", "10-09-2026", 48.0),
        ]
        last_end = datetime(2026, 9, 8, tzinfo=MADRID).timestamp()
        last_stats = {"aigues_barcelona:123_cost": [{"end": last_end, "sum": 100.0}]}

        add_stats = await self._run(invoices, last_stats)

        stats = add_stats.call_args.args[2]
        assert len(stats) == 48
        assert stats[0]["start"] == datetime(2026, 9, 7, 22, tzinfo=timezone.utc)
        assert stats[-1]["sum"] == pytest.approx(148.0)

    async def test_overlapping_invoice_keeps_full_amount(self):
        invoices = [self._invoice("07-09-2026", "10-09-2026", 30.0)]
        last_end = datetime(2026, 9, 8, tzinfo=MADRID).timestamp()
        last_stats = {"aigues_barcelona:123_cost": [{"end": last_end, "sum": 10.0}]}

        add_stats = await self._run(invoices, last_stats)

        stats = add_stats.call_args.args[2]
        assert len(stats) == 48
        assert stats[-1]["sum"] == pytest.approx(40.0)

    async def test_skips_invoices_without_period_or_not_over(self):
        invoices = [
            {"amount": 5.0},
            self._invoice("06-09-2026", "08-09-2026", 24.0),
            self._invoice("08-09-2026", "08-11-2099", 99.0),
        ]

        add_stats = await self._run(invoices, {})

        stats = add_stats.call_args.args[2]
        assert len(stats) == 48
        assert stats[-1]["sum"] == pytest.approx(24.0)

    async def test_warns_once_about_overlapping_invoices(self, caplog):
        invoices = [
            self._invoice("06-09-2026", "08-09-2026", 24.0),
            self._invoice("06-09-2026", "08-09-2026", -24.0),
        ]
        coordinator = self._coordinator(invoices)

        # Two daily checks: the warning is only logged the first time
        for _ in range(2):
            with (
                patch(
                    "custom_components.aigues_barcelona.sensor.get_db_instance",
                    return_value=coordinator.hass,
                ),
                patch(
                    "custom_components.aigues_barcelona.sensor.get_last_statistics",
                    return_value={},
                ),
                patch(
                    "custom_components.aigues_barcelona.sensor.dt_util.get_default_time_zone",
                    return_value=MADRID,
                ),
                patch(
                    "custom_components.aigues_barcelona.sensor.async_add_external_statistics"
                ),
            ):
                await coordinator.run()

        warnings = [r for r in caplog.records if "overlaps" in r.getMessage()]
        assert len(warnings) == 1
        assert "2026-09-06 - 2026-09-08" in warnings[0].getMessage()

    async def test_nothing_new(self):
        invoices = [self._invoice("06-09-2026", "08-09-2026", 24.0)]
        last_end = datetime(2026, 9, 8, tzinfo=MADRID).timestamp()
        last_stats = {"aigues_barcelona:123_cost": [{"end": last_end, "sum": 24.0}]}

        add_stats = await self._run(invoices, last_stats)

        add_stats.assert_not_called()
