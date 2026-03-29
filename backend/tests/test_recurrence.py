from datetime import date
from app.services.recurrence import expand_recurrence


def test_expands_n_occurrences():
    result = expand_recurrence(date(2026, 1, 15), "bank", 3)
    assert len(result) == 3


def test_first_occurrence_billing_month():
    result = expand_recurrence(date(2026, 1, 15), "bank", 3)
    assert result[0]["billing_month"] == date(2026, 1, 1)
    assert result[1]["billing_month"] == date(2026, 2, 1)
    assert result[2]["billing_month"] == date(2026, 3, 1)


def test_credit_card_shifts_to_next_month():
    result = expand_recurrence(date(2026, 1, 15), "credit_card", 2)
    assert result[0]["billing_month"] == date(2026, 2, 1)
    assert result[1]["billing_month"] == date(2026, 3, 1)


def test_preserves_day_of_month():
    result = expand_recurrence(date(2026, 1, 20), "bank", 3)
    assert result[0]["date"] == date(2026, 1, 20)
    assert result[1]["date"] == date(2026, 2, 20)
    assert result[2]["date"] == date(2026, 3, 20)


def test_end_of_month_clamped():
    # Jan 31 → Feb has only 28 days in 2026
    result = expand_recurrence(date(2026, 1, 31), "bank", 2)
    assert result[1]["date"] == date(2026, 2, 28)
