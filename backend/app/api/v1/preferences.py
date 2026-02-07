"""
Preferences API endpoints for managing user metric visibility settings.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas import UserPreferenceResponse, UserPreferenceUpdate
from app.services.dashboard import get_user_preferences, update_user_preferences

router = APIRouter()


# ============ Card Visibility Schemas ============

class HiddenCardsUpdate(BaseModel):
    """Schema for updating hidden cards."""
    hidden_cards: Optional[str] = Field(None, description="JSON string of hidden card IDs")


@router.get("/preferences", response_model=UserPreferenceResponse)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's preferences for dashboard metric visibility.

    Returns:
        UserPreferenceResponse: User's current preferences or defaults
    """
    return get_user_preferences(db, current_user.id)


@router.put("/preferences", response_model=UserPreferenceResponse)
def put_preferences(
    preferences: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user preferences for dashboard metric visibility.

    Args:
        preferences: Updated preference values

    Returns:
        UserPreferenceResponse: Updated preferences
    """
    return update_user_preferences(db, current_user.id, preferences)


@router.put("/hidden-cards")
async def update_hidden_cards(
    data: HiddenCardsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the list of hidden dashboard cards.
    """
    from app.models import UserPreference

    preference = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()

    if preference:
        preference.hidden_cards = data.hidden_cards
        preference.updated_at = datetime.utcnow()
    else:
        # Create if not exists
        preference = UserPreference(
            user_id=current_user.id,
            hidden_cards=data.hidden_cards
        )
        db.add(preference)

    db.commit()
    db.refresh(preference)

    return {"message": "Hidden cards updated", "hidden_cards": preference.hidden_cards}
