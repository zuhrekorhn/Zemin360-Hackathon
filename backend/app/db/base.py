import uuid

from sqlalchemy import MetaData, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Embedding boyutu, seçilen embedding modeline göre sabitlenir (docs/data-schema.md).
# 1024 = Voyage AI voyage-4. Model değişirse yeni bir migration gerekir
# (mevcut vektörler yeniden hesaplanmalı).
EMBEDDING_DIM = 1024

# Alembic migration'larında constraint isimleri deterministik olsun diye.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        sort_order=-1,  # ER diyagramındaki gibi id ilk kolon olsun
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
