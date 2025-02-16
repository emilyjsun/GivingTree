from pg_module import Charity, CharityCategory, UserCategory, get_db, UserPreferences

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from typing import Optional

from pydantic import BaseModel


class UserPrefModel(BaseModel):
    userId: str
    missionStatement: Optional[str]
    pushNotifs: Optional[bool]
    prioritizeCurrentEvents: Optional[bool]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/charities/{category}")
async def get_charities_for_category(category: str, db: Session = Depends(get_db)):
    return get_charities_for_category(db, category)

@app.get("/users/{category}")
async def get_users_for_category(category: str, db: Session = Depends(get_db)):
    return get_users_for_category(db, category)

@app.get("/charity/{id}")
async def get_charity(id: str, db: Session = Depends(get_db)):
    return get_charity(db, id)

# TODO: Safer auth

# Users can write to userpreferences

@app.put("/userpreferences")
async def update_user_preferences(userId: str, preferences: UserPrefModel, db: Session = Depends(get_db)):
    return update_user_preferences(db, userId, UserPreferences(**preferences.model_dump()))

@app.get("/userpreferences/{userId}")
async def get_user_preferences(userId: str, db: Session = Depends(get_db)):
    return get_user_preferences(db, userId)

