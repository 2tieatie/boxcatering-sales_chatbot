"""Conversations API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, User
from app.schemas.conversation import ConversationResponse, ConversationUpdate
from app.dependencies import get_current_active_user_dependency, role_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    skip: int = 0, 
    limit: int = 100,
    handover_state: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Get list of conversations (all authenticated users can view)."""
    query = db.query(Conversation)
    
    # Filter by handover state if specified
    if handover_state:
        query = query.filter(Conversation.handover_state == handover_state)
    
    conversations = query.offset(skip).limit(limit).all()
    return conversations


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Get conversation by ID (all authenticated users can view)."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Update conversation (managers can update handover state, admins can update more fields)."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    update_data = conversation_data.model_dump(exclude_unset=True)
    
    # Role-based update restrictions
    if current_user.role == "manager":
        # Managers can only update handover state and assign themselves
        allowed_fields = {"handover_state", "assigned_to"}
        update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        # Managers can only assign conversations to themselves
        if "assigned_to" in update_data and update_data["assigned_to"] != current_user.id:
            raise HTTPException(
                status_code=403, 
                detail="Managers can only assign conversations to themselves"
            )
    
    # Update fields
    for field, value in update_data.items():
        setattr(conversation, field, value)
    
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/handover/pending", response_model=List[ConversationResponse])
async def get_pending_handovers(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Get conversations pending handover (all authenticated users can view)."""
    conversations = db.query(Conversation).filter(
        Conversation.handover_state.in_(["HANDOVER_PENDING", "HANDOVER_IN_PROGRESS"])
    ).offset(skip).limit(limit).all()
    return conversations


@router.post("/{conversation_id}/take", response_model=ConversationResponse)
async def take_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Take a conversation for handover (managers only)."""
    if current_user.role != "manager":
        raise HTTPException(
            status_code=403, 
            detail="Only managers can take conversations for handover"
        )
    
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation.handover_state != "HANDOVER_PENDING":
        raise HTTPException(
            status_code=400, 
            detail="Conversation is not pending handover"
        )
    
    # Assign conversation to current user
    conversation.assigned_to = current_user.id
    conversation.handover_state = "HANDOVER_IN_PROGRESS"
    
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/{conversation_id}/resolve", response_model=ConversationResponse)
async def resolve_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Mark conversation as resolved (managers only, and only if assigned to them)."""
    if current_user.role != "manager":
        raise HTTPException(
            status_code=403, 
            detail="Only managers can resolve conversations"
        )
    
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation.assigned_to != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Can only resolve conversations assigned to you"
        )
    
    if conversation.handover_state != "HANDOVER_IN_PROGRESS":
        raise HTTPException(
            status_code=400, 
            detail="Conversation must be in progress to resolve"
        )
    
    conversation.handover_state = "RESOLVED_BY_MANAGER"
    
    db.commit()
    db.refresh(conversation)
    return conversation
