"""Chat WebSocket endpoint."""

import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.services.chatbot_service import ChatbotService
from app.services.telegram_service import TelegramService
from app.schemas.chat import ChatRequest, ChatResponse
from app.models import Conversation
from app.models.conversation import HandoverState
from app.models.message import Message, MessageSender, MessageChannel

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize services
chatbot_service = ChatbotService()
telegram_service = TelegramService()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """WebSocket endpoint for chat."""
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            chat_data = json.loads(data)
            
            # Create chat request
            chat_request = ChatRequest(
                session_id=chat_data.get("session_id"),
                sender=chat_data.get("sender", "user"),
                message=chat_data.get("message"),
                timestamp=datetime.fromisoformat(chat_data.get("timestamp"))
            )
            
            # Find or create conversation by session_id
            conversation = (
                db.query(Conversation)
                .filter(Conversation.session_id == chat_request.session_id)
                .first()
            )
            if conversation is None:
                conversation = Conversation(session_id=chat_request.session_id)
                db.add(conversation)
                db.commit()
                db.refresh(conversation)
                logger.debug(f"Created new conversation for session_id={chat_request.session_id}")
            # Get active chatbot configuration
            from app.models.chatbot_config import ChatbotConfig
            active_config = db.query(ChatbotConfig).filter(ChatbotConfig.is_active == True).first()
            
            # Set default language settings (Ukrainian by default)
            language = "uk"
            force_language = True
            
            if active_config:
                language = active_config.language
                force_language = active_config.force_language
            
            # Load OpenAI settings from system configs if present
            from app.models.system_config import SystemConfig
            cfg = {c.key: c.value for c in db.query(SystemConfig).all()}
            selected_model = cfg.get("openai_model") or None
            max_tokens = int(cfg.get("openai_max_tokens") or 0) or None
            try:
                temp_val = float(cfg.get("openai_temperature")) if cfg.get("openai_temperature") is not None else None
            except Exception:
                temp_val = None

            # Debug flag propagated via query string (?debug=1)
            qs = websocket.query_params
            debug_enabled = str(qs.get("debug", "0")).lower() in {"1", "true", "yes"}

            # Persist incoming user message (respect conversation_logging flag)
            try:
                should_log = True
                if active_config and active_config.conversation_logging is not None:
                    should_log = bool(active_config.conversation_logging)
                if should_log:
                    user_message = Message(
                        chat_id=conversation.id,
                        sender=MessageSender.USER,
                        channel=MessageChannel.WEB,
                        text=chat_request.message,
                        timestamp=chat_request.timestamp,
                    )
                    db.add(user_message)
                    db.commit()
            except Exception as msg_err:
                db.rollback()
                logger.error(f"Failed to save user message: {msg_err}")
                # Continue processing; DB failure shouldn't break user chat entirely

            # Process message with AI (respect model capabilities)
            chat_response = await chatbot_service.process_message(
                chat_request,
                language=language,
                force_language=force_language,
                model=selected_model,
                temperature=temp_val,
                max_tokens=max_tokens,
                debug=debug_enabled,
                config=(
                    {
                        "company_name": active_config.company_name,
                        "business_context": active_config.business_context,
                        "specializations": active_config.specializations,
                        "friendly_tone": active_config.friendly_tone,
                        "professional_style": active_config.professional_style,
                        "suggestive_responses": active_config.suggestive_responses,
                        "manager_handover": active_config.manager_handover,
                        "fallback_message": active_config.fallback_message,
                        "handover_message": active_config.handover_message,
                    }
                    if active_config
                    else None
                ),
            )
            
            # Persist bot response and update conversation state
            try:
                should_log = True
                if active_config and active_config.conversation_logging is not None:
                    should_log = bool(active_config.conversation_logging)
                if should_log:
                    bot_message = Message(
                        chat_id=conversation.id,
                        sender=MessageSender.BOT,
                        channel=MessageChannel.WEB,
                        text=chat_response.response,
                    )
                    db.add(bot_message)

                # Update conversation handover fields when applicable
                if chat_response.handover_to_manager:
                    # If already in progress, keep it; otherwise mark as pending
                    if conversation.handover_state not in {HandoverState.HANDOVER_IN_PROGRESS}:
                        conversation.handover_state = HandoverState.HANDOVER_PENDING
                    # Persist handover metadata
                    conversation.handover_reason = (
                        (chat_response.handover_reason.value if hasattr(chat_response.handover_reason, "value") else str(chat_response.handover_reason))
                        if chat_response.handover_reason is not None else conversation.handover_reason
                    )
                    conversation.handover_reason_description = chat_response.handover_reason_description or conversation.handover_reason_description
                else:
                    # Do not override if a manager is already involved; otherwise remain NONE
                    if conversation.handover_state in {None, HandoverState.NONE}:
                        conversation.handover_state = HandoverState.NONE

                db.commit()
                db.refresh(conversation)
            except Exception as save_err:
                db.rollback()
                logger.error(f"Failed to save bot message or update conversation: {save_err}")

            # Send response back to client
            await websocket.send_text(json.dumps(chat_response.model_dump()))
            
            # If handover is needed, send Telegram notification
            if chat_response.handover_to_manager:
                await telegram_service.send_handover_notification(
                    chat_request.session_id,
                    chat_request.message,
                    chat_response
                )
                
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()
