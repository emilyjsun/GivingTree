from api.pg_module.crud import put_user_preferences
from pg_module import Charity, CharityCategory, UserCategory, get_db, UserPreferences, put_user_preferences, create_user_preferences
from users import CharityInputCategorizer
from web3_utils.interact_with_contract import enroll_user

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
        # First create user preferences in database
        user_prefs = create_user_preferences(
            db=db,
            user_id=request.userId,
            mission_statement=request.missionStatement,
            push_notifs=request.pushNotifs,
            prioritize_events=request.prioritizeCurrentEvents
        )
        
        # Process mission statement to get categories
        categorizer = CharityInputCategorizer()
        categorization_result = categorizer.process_input(
            user_input=request.missionStatement,
            instant_updates=request.pushNotifs,
            user_id=request.userId
        )
        
        # Get top 3 categories for contract
        categories = categorization_result['categories']
        topics = [cat for cat, _ in categories[:3]]

            
        # Calculate charity allocations
        charity_addresses = []
        charity_percentages = []
        total_score = sum(score for _, score in categories[:3])
        
        for category, score in categories[:3]:
            # Get charity for this category
            charity = db.query(Charity).filter(
                Charity.category == category
            ).first()
            
            if charity:
                charity_addresses.append(charity.wallet_address)
                percentage = int((score / total_score) * 100)
                charity_percentages.append(percentage)
        
        # Adjust percentages to sum to 100 using weighted distribution
        if charity_percentages:
            current_sum = sum(charity_percentages)
            if current_sum != 100:
                # Calculate adjustment factor
                adjustment = (100 - current_sum) / len(charity_percentages)
                # Distribute remaining percentage proportionally
                charity_percentages = [p + adjustment for p in charity_percentages]
                # Round to integers while preserving sum of 100
                charity_percentages = [round(p) for p in charity_percentages[:-1]] + [
                    100 - sum(round(p) for p in charity_percentages[:-1])
                ]
            
        # Enroll user in smart contract
        contract_result = enroll_user(
            contract,
            topics=topics,
            charities=charity_addresses,
            charityPercents=charity_percentages
        )
        
        return {
            "status": "success",
            "data": {
                "userId": user_prefs.userid,
                "missionStatement": user_prefs.missionStatement,
                "pushNotifications": user_prefs.pushNotifications,
                "prioritizeCurrentEvents": user_prefs.prioritizeCurrentEvents,
                "categories": categories,
                "contract_tx": contract_result['transactionHash'].hex()
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error creating preferences: {str(e)}"
        )