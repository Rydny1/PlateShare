from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    phone_nr: Mapped[str] = mapped_column(String(30), unique=True, index=True)


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    phone_nr: Mapped[str] = mapped_column(String(30), unique=True, index=True)


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_offer_quantity_positive"),
        CheckConstraint("remaining_quantity >= 0", name="check_offer_remaining_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[int] = mapped_column(Integer)
    remaining_quantity: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        UniqueConstraint("offer_id", "student_id", name="unique_student_offer_claim"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)