from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Solver(Base):
    __tablename__ = "solvers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)

    parameters: Mapped[list["SolverParameter"]] = relationship(
        back_populates="solver", cascade="all, delete-orphan"
    )


class SolverParameter(Base):
    __tablename__ = "solver_parameters"
    __table_args__ = (UniqueConstraint("solver_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    solver_id: Mapped[int] = mapped_column(ForeignKey("solvers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    solver: Mapped["Solver"] = relationship(back_populates="parameters")
