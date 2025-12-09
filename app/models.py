from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, Float, Text
from sqlalchemy.orm import relationship
from .database import Base
import enum

class TyreCondition(str, enum.Enum):
    good = "good"
    bad = "bad"

class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.user)

    cars = relationship("Car", back_populates="user", cascade="all, delete-orphan")


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    make = Column(String, nullable=False)
    model = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    plate = Column(String, nullable=False)

    user = relationship("User", back_populates="cars")
    inspections = relationship(
        "Inspection", back_populates="car", cascade="all, delete-orphan"
    )


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime, nullable=False)
    frontLeft = Column(Enum(TyreCondition), nullable=False)
    frontRight = Column(Enum(TyreCondition), nullable=False)
    rearLeft = Column(Enum(TyreCondition), nullable=False)
    rearRight = Column(Enum(TyreCondition), nullable=False)
    notes = Column(Text, nullable=True)

    car = relationship("Car", back_populates="inspections")



