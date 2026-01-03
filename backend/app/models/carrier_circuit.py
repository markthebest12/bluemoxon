"""Circuit breaker state for carrier APIs."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CarrierCircuit(Base):
    """Tracks circuit breaker state per carrier."""

    __tablename__ = "carrier_circuit_state"

    carrier_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    circuit_open_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
