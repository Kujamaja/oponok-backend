from datetime import timedelta
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from . import models, schemas
from .database import engine, Base, get_db
from .auth import (
    authenticate_user,
    create_access_token,
    hash_password,
    get_current_user,
)

from .models import TyreCondition


app = FastAPI(title="oponOK - backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)



@app.post("/register", response_model=schemas.UserOut, tags=["auth"])
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already in use")

    db_user = models.User(
        name=user.name,
        email=user.email,
        phone=user.phone,
        role=user.role,
        password_hash=hash_password(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/login", response_model=schemas.Token, tags=["auth"])
def login(
    data: schemas.LoginRequest,
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=60),
    )
    return {"access_token": access_token, "token_type": "bearer"}


'''
@app.post("/login", tags=["auth"])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # form_data.username = email
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},  
        expires_delta=timedelta(minutes=60),
    )
    return {"access_token": access_token, "token_type": "bearer"}
'''


@app.get("/me", response_model=schemas.MeResponse, tags=["auth"])
def me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    cars_q = db.query(models.Car).filter(models.Car.user_id == current_user.id)
    cars = cars_q.all()
    cars_assigned = len(cars)


    if cars:
        car_ids = [c.id for c in cars]
        inspections_total = (
            db.query(models.Inspection)
            .filter(models.Inspection.car_id.in_(car_ids))
            .count()
        )
    else:
        inspections_total = 0

    failed_cars = 0
    for car in cars:
        last = (
            db.query(models.Inspection)
            .filter(models.Inspection.car_id == car.id)
            .order_by(models.Inspection.date.desc())
            .first()
        )

        if not last:
            continue

        if (
            last.frontLeft == TyreCondition.bad
            or last.frontRight == TyreCondition.bad
            or last.rearLeft == TyreCondition.bad
            or last.rearRight == TyreCondition.bad
        ):
            failed_cars += 1

    return schemas.MeResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        phone=current_user.phone,
        role=current_user.role,
        cars_assigned=cars_assigned,
        inspections_total=inspections_total,
        failed_cars=failed_cars,
    )



@app.get("/cars", response_model=List[schemas.CarOut], tags=["cars"])
def list_cars(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == models.UserRole.admin:
        cars = db.query(models.Car).all()
    else:
        cars = db.query(models.Car).filter(models.Car.user_id == current_user.id).all()
    return cars


@app.post("/cars", response_model=schemas.CarOut, tags=["cars"])
def create_car(
    car: schemas.CarCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_car = models.Car(
        user_id=current_user.id,
        **car.model_dump(),
    )
    db.add(db_car)
    db.commit()
    db.refresh(db_car)
    return db_car


@app.get("/cars/{car_id}", response_model=schemas.CarOut, tags=["cars"])
def get_car(
    car_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    car = db.get(models.Car, car_id)
    if not car:
        raise HTTPException(404, "Car not found")
    if current_user.role != models.UserRole.admin and car.user_id != current_user.id:
        raise HTTPException(403, "Not your car")
    return car


@app.put("/cars/{car_id}", response_model=schemas.CarOut, tags=["cars"])
def update_car(
    car_id: int,
    car_in: schemas.CarCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    car = db.get(models.Car, car_id)
    if not car:
        raise HTTPException(404, "Car not found")
    if current_user.role != models.UserRole.admin and car.user_id != current_user.id:
        raise HTTPException(403, "Not your car")

    for field, value in car_in.model_dump().items():
        setattr(car, field, value)
    db.commit()
    db.refresh(car)
    return car


@app.delete("/cars/{car_id}", tags=["cars"])
def delete_car(
    car_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    car = db.get(models.Car, car_id)
    if not car:
        raise HTTPException(404, "Car not found")
    if current_user.role != models.UserRole.admin and car.user_id != current_user.id:
        raise HTTPException(403, "Not your car")

    db.delete(car)
    db.commit()
    return {"status": "deleted"}


@app.get(
    "/inspections/{car_id}",
    response_model=List[schemas.InspectionOut],
    tags=["inspections"],
)
def list_inspections(
    car_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    car = db.get(models.Car, car_id)
    if not car:
        raise HTTPException(404, "Car not found")
    if current_user.role != models.UserRole.admin and car.user_id != current_user.id:
        raise HTTPException(403, "Not your car")

    return (
        db.query(models.Inspection)
        .filter(models.Inspection.car_id == car_id)
        .order_by(models.Inspection.date.desc())
        .all()
    )


@app.post(
    "/inspections/{car_id}",
    response_model=schemas.InspectionOut,
    tags=["inspections"],
)
def create_inspection(
    car_id: int,
    inspection: schemas.InspectionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    car = db.get(models.Car, car_id)
    if not car:
        raise HTTPException(404, "Car not found")
    if current_user.role != models.UserRole.admin and car.user_id != current_user.id:
        raise HTTPException(403, "Not your car")

    db_insp = models.Inspection(
        car_id=car_id,
        **inspection.model_dump(),
    )
    db.add(db_insp)
    db.commit()
    db.refresh(db_insp)
    return db_insp


@app.put("/inspections/{inspection_id}", response_model=schemas.InspectionOut, tags=["inspections"],)
def update_inspection(
    inspection_id: int,
    inspection_in: schemas.InspectionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    insp = db.get(models.Inspection, inspection_id)
    if not insp:
        raise HTTPException(404, "Inspection not found")

    car = db.get(models.Car, insp.car_id)
    if not car:
        raise HTTPException(404, "Car not found")
    if current_user.role != models.UserRole.admin and car.user_id != current_user.id:
        raise HTTPException(403, "Not your car")

    for field, value in inspection_in.model_dump().items():
        setattr(insp, field, value)
    db.commit()
    db.refresh(insp)
    return insp


@app.delete("/inspections/{inspection_id}", tags=["inspections"])
def delete_inspection(
    inspection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    insp = db.get(models.Inspection, inspection_id)
    if not insp:
        raise HTTPException(404, "Inspection not found")

    car = db.get(models.Car, insp.car_id)
    if not car:
        raise HTTPException(404, "Car not found")
    if current_user.role != models.UserRole.admin and car.user_id != current_user.id:
        raise HTTPException(403, "Not your car")

    db.delete(insp)
    db.commit()
    return {"status": "deleted"}
