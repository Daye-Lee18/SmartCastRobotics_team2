"""Alert/status models aligned to create_tables.sql."""

from __future__ import annotations

from ._base import (
    SCHEMA,
    Base,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    String,
)


class AlertsStat(Base):
    __tablename__ = "alerts_stat"
    __table_args__ = (
        CheckConstraint("severity IN ('info', 'warning', 'critical')", name="chk_alerts_severity"),
        {"schema": SCHEMA},
    )

    id = Column(String, primary_key=True)
    res_id = Column(String(10), ForeignKey(f"{SCHEMA}.res.res_id"), nullable=False)
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False, server_default="info")
    error_code = Column(String, server_default="")
    message = Column(String, nullable=False)
    abnormal_value = Column(String, server_default="")
    zone = Column(String)
    timestamp = Column("timestamp", String, nullable=False)
    resolved_at = Column(String)
    acknowledged = Column(Boolean, nullable=False, server_default="false")


Alert = AlertsStat
