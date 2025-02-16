from pg_module import get_db
from pg_module.models import UserCategory
from utils.web3_utils import enroll_user_in_contract
from typing import List
import json

async def create_new_user(wallet_address: str, mission_statement: str, instant_updates: bool = False):
    """Create new user and initialize their preferences"""
    try:
        with next(get_db()) as db:
            # First, analyze mission statement to get categories
            from services.user_manager import categorize_mission_statement
            categories = categorize_mission_statement(mission_statement)
            
            # Store user categories
            for category, score in categories:
                user_category = UserCategory(
                    userid=wallet_address,
                    category=category
                )
                db.add(user_category)
            
            # Get top 3 categories for contract
            top_categories = [cat for cat, _ in categories[:3]]
            while len(top_categories) < 3:  # Pad if needed
                top_categories.append("")
                
            # Get charities for these categories
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
            
            # Adjust percentages to sum to 100
            while sum(charity_percentages) < 100 and charity_percentages:
                charity_percentages[0] += 1
                
            # Enroll in smart contract
            contract_result = await enroll_user_in_contract(
                wallet_address,
                top_categories,
                charity_addresses,
                charity_percentages
            )
            
            db.commit()
            
            return {
                "wallet_address": wallet_address,
                "categories": categories,
                "contract_tx": contract_result['tx_hash']
            }
            
    except Exception as e:
        db.rollback()
        raise e 