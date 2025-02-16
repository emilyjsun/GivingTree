from sqlalchemy.orm import Session
from typing import Optional, List
from .models import UserCategory, CharityCategory

def get_users_for_category(db: Session, category: str) -> Optional[List[UserCategory]]:
    return db.query(UserCategory).filter(UserCategory.category == category).all()

def get_charities_for_category(db: Session, category: str)  -> Optional[List[CharityCategory]]:
    return db.query(CharityCategory).filter(CharityCategory.category == category).all()