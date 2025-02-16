from sqlalchemy.orm import Session
from typing import Optional, List
from .models import UserCategory, CharityCategory, Charity

def get_users_for_category(db: Session, category: str) -> Optional[List[UserCategory]]:
    return db.query(UserCategory).filter(UserCategory.category == category).all()

def get_charities_for_category(db: Session, category: str)  -> Optional[List[Charity]]:
    # I want to return rows from Charity where there exists a row in CharityCategory with the same category and that charity name

    return db.query(Charity).join(CharityCategory, Charity.name == CharityCategory.charityname).filter(CharityCategory.category == category).all()