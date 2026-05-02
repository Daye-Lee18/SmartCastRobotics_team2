from __future__ import annotations

from ._base import (
    SCHEMA,
    Base,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    Boolean,
)

class Alert(Base):
    """알림 (public.alerts)."""

    __tablename__ = "alerts"

    id = Column(String, primary_key=True, index=True)
    equipment_id = Column(String, nullable=True, default="")
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="info")
    error_code = Column(String, nullable=True, default="")
    message = Column(String, nullable=False)
    abnormal_value = Column(String, nullable=True, default="")
    zone = Column(String, nullable=True)
    timestamp = Column(String, nullable=False)
    resolved_at = Column(String, nullable=True)
    acknowledged = Column(Boolean, nullable=False, default=False)

