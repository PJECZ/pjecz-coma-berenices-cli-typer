"""
Modelos ORM para audiencias
"""

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class Audiencia(Base):
    """Audiencia"""

    # Nombre de la tabla
    __tablename__ = "audiencias"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    fecha: Mapped[str] = mapped_column(String)
    hora_inicio: Mapped[str] = mapped_column(String)
    hora_fin: Mapped[str] = mapped_column(String)
    materia: Mapped[str] = mapped_column(String)
    autoridad: Mapped[str] = mapped_column(String)
    numero_expediente: Mapped[str] = mapped_column(String)
    sala: Mapped[str] = mapped_column(String)
    numero_sala: Mapped[int] = mapped_column(Integer)  # Se separa para poder ordenar
    tipo_audiencia: Mapped[str] = mapped_column(String)
    voceos: Mapped[int] = mapped_column(Integer, default=0)

    # Reestricciones de la tabla
    __table_args__ = (
        UniqueConstraint(
            "fecha",
            "hora_inicio",
            "sala",
            name="uix_audiencia",
        ),
    )
