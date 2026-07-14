from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from utils.basemodel import metadata


class Base(DeclarativeBase):
    metadata = metadata


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)


class DictionaryItem(Timestamped, Base):
    __tablename__ = "dictionary_items"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dictionary_code: Mapped[str] = mapped_column(String(100))
    hh_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(500))
    __table_args__ = (UniqueConstraint("dictionary_code", "hh_id"),)


class NamedItem(Timestamped):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    hh_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(500))


class Area(NamedItem, Base):
    __tablename__ = "areas"
    parent_hh_id: Mapped[str | None] = mapped_column(String(100), ForeignKey("areas.hh_id"))
    __table_args__ = (UniqueConstraint("hh_id"),)


class Country(NamedItem, Base):
    __tablename__ = "countries"
    __table_args__ = (UniqueConstraint("hh_id"),)


class ProfessionalRoleCategory(NamedItem, Base):
    __tablename__ = "professional_role_categories"
    __table_args__ = (UniqueConstraint("hh_id"),)


class ProfessionalRole(NamedItem, Base):
    __tablename__ = "professional_roles"
    category_hh_id: Mapped[str] = mapped_column(String(100), ForeignKey("professional_role_categories.hh_id"))
    __table_args__ = (UniqueConstraint("category_hh_id", "hh_id", name="uq_professional_roles_category_hh_id_hh_id"),)


class Industry(NamedItem, Base):
    __tablename__ = "industries"
    parent_hh_id: Mapped[str | None] = mapped_column(String(100), ForeignKey("industries.hh_id"))
    __table_args__ = (UniqueConstraint("hh_id"),)


class MetroCity(NamedItem, Base):
    __tablename__ = "metro_cities"
    __table_args__ = (UniqueConstraint("hh_id"),)


class MetroLine(NamedItem, Base):
    __tablename__ = "metro_lines"
    city_hh_id: Mapped[str] = mapped_column(String(100), ForeignKey("metro_cities.hh_id"))
    __table_args__ = (UniqueConstraint("hh_id"),)


class MetroStation(NamedItem, Base):
    __tablename__ = "metro_stations"
    line_hh_id: Mapped[str] = mapped_column(String(100), ForeignKey("metro_lines.hh_id"))
    lat: Mapped[str | None] = mapped_column(String(40))
    lng: Mapped[str | None] = mapped_column(String(40))
    order: Mapped[int | None]
    __table_args__ = (UniqueConstraint("hh_id"),)


class Language(NamedItem, Base):
    __tablename__ = "languages"
    __table_args__ = (UniqueConstraint("hh_id"),)


class SyncState(Base):
    __tablename__ = "dictionary_sync_states"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="never")
    last_attempt_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_error: Mapped[str | None] = mapped_column(Text)
