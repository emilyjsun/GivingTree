from sqlalchemy.orm import Session
from typing import Optional, List
from .models import UserCategory, CharityCategory, Charity, UserPreferences

def get_users_for_category(db: Session, category: str) -> Optional[List[UserCategory]]:
    return db.query(UserCategory).filter(UserCategory.category == category).all()

def get_charities_for_category(db: Session, category: str)  -> Optional[List[Charity]]:
    # I want to return rows from Charity where there exists a row in CharityCategory with the same category and that charity name

    return db.query(Charity).join(CharityCategory, Charity.name == CharityCategory.charityname).filter(CharityCategory.category == category).all()

def create_user_preferences(db: Session, user_id: str, mission_statement: str, push_notifs: bool, prioritize_events: bool):
    """Create new user preferences in database"""
    try:
        user_prefs = UserPreferences(
            userid=user_id,
            missionStatement=mission_statement,
            pushNotifications=push_notifs,
            prioritizeCurrentEvents=prioritize_events
        )
        
        db.add(user_prefs)
        db.commit()
        db.refresh(user_prefs)
        
        return user_prefs
    except Exception as e:
        db.rollback()
        raise e