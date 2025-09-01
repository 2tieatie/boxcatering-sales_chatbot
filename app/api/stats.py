"""Statistics API endpoints for dashboard counters."""

from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import get_db
from app.dependencies import get_current_active_user_dependency
from app.models import Conversation, Customer, Order, User
from app.models.conversation import HandoverState


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary")
async def get_stats_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
) -> Dict[str, int]:
    """Return summary counters for the dashboard.

    - total_conversations: total number of conversations
    - active_orders: orders not processed yet (is_processed == False)
    - total_customers: total number of customers
    - handovers: conversations pending or in-progress handover
    """

    total_conversations: int = db.query(func.count(Conversation.id)).scalar() or 0

    active_orders: int = (
        db.query(func.count(Order.id)).filter(Order.is_processed.is_(False)).scalar() or 0
    )

    total_customers: int = db.query(func.count(Customer.id)).scalar() or 0

    handovers: int = (
        db.query(func.count(Conversation.id))
        .filter(
            Conversation.handover_state.in_(
                [HandoverState.HANDOVER_PENDING, HandoverState.HANDOVER_IN_PROGRESS]
            )
        )
        .scalar()
        or 0
    )

    return {
        "total_conversations": total_conversations,
        "active_orders": active_orders,
        "total_customers": total_customers,
        "handovers": handovers,
    }


