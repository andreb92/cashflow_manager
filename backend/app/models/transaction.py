from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, DateTime, Integer, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.user import gen_uuid


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[str] = mapped_column(String(10))
    detail: Mapped[str] = mapped_column(String(500))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    payment_method_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("payment_methods.id")
    )
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("categories.id"), nullable=True
    )
    transaction_direction: Mapped[str] = mapped_column(String(20))
    billing_month: Mapped[str] = mapped_column(String(10))
    recurrence_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    installment_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    installment_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parent_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("transactions.id"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
