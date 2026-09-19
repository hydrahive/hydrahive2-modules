from datetime import datetime, timezone

from backend.sla import calculate_deadlines, default_profile, effective_deadline


START = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


def test_default_profile_calculates_priority_deadlines():
    deadlines = calculate_deadlines(START, "urgent")

    assert deadlines["response_due_at"] == "2026-01-10T16:00:00Z"
    assert deadlines["resolution_due_at"] == "2026-01-11T12:00:00Z"


def test_low_priority_uses_longer_default_window():
    profile = default_profile()
    deadlines = calculate_deadlines(START, "low", profile)

    assert deadlines["response_due_at"] == "2026-01-13T12:00:00Z"
    assert deadlines["resolution_due_at"] == "2026-01-20T12:00:00Z"


def test_manual_deadline_overrides_sla_and_can_be_reset():
    calculated = "2026-01-15T12:00:00Z"
    manual = "2026-01-12T09:30:00Z"

    assert effective_deadline(calculated, manual) == (manual, "manual")
    assert effective_deadline(calculated, None) == (calculated, "sla")
