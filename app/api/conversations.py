"""Conversations API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, User, Message
from app.schemas.conversation import ConversationResponse, ConversationUpdate
from app.schemas.message import MessageResponse
from app.dependencies import get_current_active_user_dependency, role_service
from app.models.conversation import HandoverState

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
        # Accept either enum name or value; normalize to value
        normalized = handover_state
        try:
            # Try map from enum name like 'HANDOVER_PENDING'
            normalized = HandoverState[handover_state].value
        except Exception:
            # Could already be a value like 'handover_pending'
            normalized = handover_state
        query = query.filter(Conversation.handover_state == normalized)
    
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
    """Take a conversation for handover (manager or higher)."""
    role_service.require_manager_or_higher(current_user)
    
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation.handover_state != HandoverState.HANDOVER_PENDING:
        raise HTTPException(
            status_code=400, 
            detail="Conversation is not pending handover"
        )
    
    # Assign conversation to current user
    conversation.assigned_to = current_user.id
    conversation.handover_state = HandoverState.HANDOVER_IN_PROGRESS
    
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/{conversation_id}/resolve", response_model=ConversationResponse)
async def resolve_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Mark conversation as resolved (manager or higher, only if assigned to them)."""
    role_service.require_manager_or_higher(current_user)
    
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation.assigned_to != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Can only resolve conversations assigned to you"
        )
    
    if conversation.handover_state != HandoverState.HANDOVER_IN_PROGRESS:
        raise HTTPException(
            status_code=400, 
            detail="Conversation must be in progress to resolve"
        )
    
    conversation.handover_state = HandoverState.RESOLVED_BY_MANAGER
    
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
):
    """Get messages for a conversation."""
    # Ensure conversation exists
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = (
        db.query(Message)
        .filter(Message.chat_id == conversation_id)
        .order_by(Message.timestamp.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return messages
