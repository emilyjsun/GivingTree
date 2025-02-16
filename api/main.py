from api.pg_module.crud import put_user_preferences
from pg_module import Charity, CharityCategory, UserCategory, get_db, UserPreferences, put_user_preferences, create_user_preferences

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from typing import Optional

from pydantic import BaseModel


class UserPrefModel(BaseModel):
    userId: str
    missionStatement: Optional[str]
    pushNotifs: Optional[bool]
    prioritizeCurrentEvents: Optional[bool]

class CreatePreferencesRequest(BaseModel):
    userId: str
    missionStatement: str
    pushNotifs: bool
    prioritizeCurrentEvents: bool

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
    return put_user_preferences(db, userId, UserPreferences(**preferences.model_dump()))

@app.get("/userpreferences/{userId}")
async def get_user_preferences(userId: str, db: Session = Depends(get_db)):
    return get_user_preferences(db, userId)


@app.post("/userpreferences")
async def create_user_preferences(userId: str, preferences: UserPrefModel, db: Session = Depends(get_db)):
    return create_user_preferences(db, userId, UserPreferences(**preferences.model_dump()))

@app.post("/userpreferences/create")
async def create_preferences(
    request: CreatePreferencesRequest,
    db: Session = Depends(get_db)
):
    try:
        user_prefs = create_user_preferences(
            db=db,
            user_id=request.userId,
            mission_statement=request.missionStatement,
            push_notifs=request.pushNotifs,
            prioritize_events=request.prioritizeCurrentEvents
        )
        
        return {
            "status": "success",
            "data": {
                "userId": user_prefs.userid,
                "missionStatement": user_prefs.missionStatement,
                "pushNotifications": user_prefs.pushNotifications,
                "prioritizeCurrentEvents": user_prefs.prioritizeCurrentEvents
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error creating preferences: {str(e)}"
        )