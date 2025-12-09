from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from .models import UserRole, TyreCondition



class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    role: UserRole = UserRole.user


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    role: UserRole



class CarBase(BaseModel):
    make: str
    model: str
    year: int
    plate: str


class CarCreate(CarBase):
    pass


class CarOut(CarBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class InspectionBase(BaseModel):
    date: datetime
    frontLeft: TyreCondition
    frontRight: TyreCondition
    rearLeft: TyreCondition
    rearRight: TyreCondition
    notes: Optional[str] = None



class InspectionCreate(InspectionBase):
    pass


class InspectionOut(InspectionBase):
    id: int
    car_id: int

    class Config:
        from_attributes = True


class MeResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    role: UserRole
    cars_assigned: int
    inspections_total: int
    failed_cars: int

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
