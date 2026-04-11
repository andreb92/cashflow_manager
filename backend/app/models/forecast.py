from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, Integer, Text, ForeignKey, DateTime, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.user import gen_uuid


class Forecast(Base):
    __tablename__ = "forecasts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    base_year: Mapped[int] = mapped_column(Integer)
    projection_years: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ForecastLine(Base):
    __tablename__ = "forecast_lines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    forecast_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("forecasts.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    detail: Mapped[str] = mapped_column(Text)
    base_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    payment_method_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("payment_methods.id", ondelete="SET NULL"), nullable=True
    )
    billing_day: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ForecastAdjustment(Base):
    __tablename__ = "forecast_adjustments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    forecast_line_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("forecast_lines.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    valid_from: Mapped[str] = mapped_column(String(10))
    new_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    adjustment_type: Mapped[str] = mapped_column(String(20), default="fixed", server_default="fixed")

    __table_args__ = (
        CheckConstraint("adjustment_type IN ('fixed', 'percentage')", name="ck_adjustment_type"),
    )
