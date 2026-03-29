from typing import Optional
from sqlalchemy import String, Boolean, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.user import gen_uuid


class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_pm_user_name"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(50))
    is_main_bank: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_bank_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("payment_methods.id"), nullable=True
    )
    opening_balance: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class MainBankHistory(Base):
    __tablename__ = "main_bank_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    payment_method_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("payment_methods.id")
    )
    valid_from: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD first of month
    opening_balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
