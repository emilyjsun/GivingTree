from api.pg_module import put_user_preferences, Charity, CharityCategory, UserCategory, get_db, UserPreferences, put_user_preferences, create_user_preferences, get_charities_for_category, get_users_for_category, get_user_preferences, Counter

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
async def get_chars(category: str, db: Session = Depends(get_db)):
    return get_charities_for_category(db, category)

@app.get("/users/{category}")
async def get_user(category: str, db: Session = Depends(get_db)):
    return get_users_for_category(db, category)

@app.get("/charity/{id}")
async def get_charity(id: str, db: Session = Depends(get_db)):
    return get_charity(db, id)

@app.put("/userpreferences")
async def update_user_preferences(userId: str, preferences: UserPrefModel, db: Session = Depends(get_db)):
    return put_user_preferences(db, userId, UserPreferences(**preferences.model_dump()))

@app.get("/userpreferences/{userId}")
async def get_prefs(userId: str, db: Session = Depends(get_db)):
    return get_user_preferences(db, userId)


@app.post("/userpreferences")
async def create_prefs(userId: str, preferences: UserPrefModel, db: Session = Depends(get_db)):
    return create_user_preferences(db, userId, UserPreferences(**preferences.model_dump()))

@app.post("/counter")
async def setCounter(userId: str, count: int, db: Session = Depends(get_db)):
    matches = db.query(Counter).filter(Counter.userid == userId)
    if matches.count() > 0:
        match = matches.first()
        match.countvalue = count
        db.commit()
        return {"count": count}
    else:
        db.add(Counter(userid=userId, countvalue=count))
        db.commit()
        return {"count": count}

@app.get("/counter/{userId}")
async def getCounter(userId: str, db: Session = Depends(get_db)):
    match = db.query(Counter).filter(Counter.userid == userId).first()
    if match:
        return {"count": match.countvalue}
    
    return {"count": 0}