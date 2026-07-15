from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.dictionaries import Base, Timestamped


class FilterPreset(Timestamped, Base):
    __tablename__ = "filter_presets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    hh_user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(63), nullable=False)
    text: Mapped[str | None] = mapped_column(Text)
    excluded_text: Mapped[str | None] = mapped_column(Text)
    salary: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(10))
    salary_mode: Mapped[str | None] = mapped_column(String(50))
    period: Mapped[int | None] = mapped_column(Integer)
    date_from: Mapped[str | None] = mapped_column(String(30))
    date_to: Mapped[str | None] = mapped_column(String(30))
    order_by: Mapped[str | None] = mapped_column(String(50))
    premium: Mapped[bool | None] = mapped_column(Boolean)
    accept_temporary: Mapped[bool | None] = mapped_column(Boolean)
    no_magic: Mapped[bool | None] = mapped_column(Boolean)
    top_lat: Mapped[float | None] = mapped_column(Float)
    bottom_lat: Mapped[float | None] = mapped_column(Float)
    left_lng: Mapped[float | None] = mapped_column(Float)
    right_lng: Mapped[float | None] = mapped_column(Float)
    sort_point_lat: Mapped[float | None] = mapped_column(Float)
    sort_point_lng: Mapped[float | None] = mapped_column(Float)

    values: Mapped[list["FilterPresetValue"]] = relationship(
        back_populates="preset", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (UniqueConstraint("hh_user_id", "name", name="uq_filter_presets_hh_user_id_name"),)


class FilterPresetValue(Base):
    __tablename__ = "filter_preset_values"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    preset_id: Mapped[UUID] = mapped_column(
        ForeignKey("filter_presets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parameter_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(200), nullable=False)

    preset: Mapped["FilterPreset"] = relationship(back_populates="values")

    __table_args__ = (
        UniqueConstraint("preset_id", "parameter_name", "value", name="uq_filter_preset_values_pnv"),
    )
