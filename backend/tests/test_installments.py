from datetime import date
from app.services.installments import expand_installments


def test_splits_into_n_installments():
    result = expand_installments(100.0, date(2026, 1, 15), 4)
    assert len(result) == 4


def test_installment_amounts_sum_to_total():
    result = expand_installments(100.0, date(2026, 1, 15), 3)
    total = sum(r["amount"] for r in result)
    assert abs(total - 100.0) < 0.001


def test_last_installment_absorbs_rounding():
    # 100 / 3 = 33.33 * 3 = 99.99, last gets 33.34
    result = expand_installments(100.0, date(2026, 1, 15), 3)
    assert result[0]["amount"] == round(100.0 / 3, 2)
    assert result[2]["amount"] == round(100.0 - round(100.0 / 3, 2) * 2, 2)


def test_billing_months_start_next_month():
    # installments always use revolving → next month + i
    result = expand_installments(60.0, date(2026, 1, 15), 3)
    assert result[0]["billing_month"] == date(2026, 2, 1)
    assert result[1]["billing_month"] == date(2026, 3, 1)
    assert result[2]["billing_month"] == date(2026, 4, 1)


def test_installment_index():
    result = expand_installments(100.0, date(2026, 1, 15), 3)
    assert result[0]["installment_index"] == 1
    assert result[1]["installment_index"] == 2
    assert result[2]["installment_index"] == 3
