"""User 도메인 모델 — UserAccount."""

from __future__ import annotations

from ._base import SCHEMA, Base, CheckConstraint, Column, Integer, String


class UserAccount(Base):
    """사용자 정보 (customer/admin/operator/fms)."""

    __tablename__ = "user_account"
    __table_args__ = (
        CheckConstraint("role IN ('customer', 'admin', 'operator', 'fms')", name="chk_user_role"),
        {"schema": SCHEMA},
    )

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    co_nm = Column(String, nullable=False)
    user_nm = Column(String, nullable=False)
    role = Column(String)
    phone = Column(String)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
