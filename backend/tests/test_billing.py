from datetime import date
from app.services.billing import billing_month


def test_bank_current_month():
    assert billing_month("bank", date(2026, 3, 15)) == date(2026, 3, 1)


def test_debit_card_current_month():
    assert billing_month("debit_card", date(2026, 3, 31)) == date(2026, 3, 1)


def test_prepaid_current_month():
    assert billing_month("prepaid", date(2026, 3, 1)) == date(2026, 3, 1)


def test_cash_current_month():
    assert billing_month("cash", date(2026, 12, 31)) == date(2026, 12, 1)


def test_credit_card_next_month():
    assert billing_month("credit_card", date(2026, 3, 15)) == date(2026, 4, 1)


def test_revolving_next_month():
    assert billing_month("revolving", date(2026, 3, 15)) == date(2026, 4, 1)


def test_credit_card_december_wraps_to_january():
    assert billing_month("credit_card", date(2026, 12, 15)) == date(2027, 1, 1)


def test_unknown_type_raises():
    import pytest
    with pytest.raises(ValueError):
        billing_month("unknown", date(2026, 1, 1))
