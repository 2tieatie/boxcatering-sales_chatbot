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

            # Process message with AI (respect model capabilities)
            chat_response = await chatbot_service.process_message(
                chat_request,
                language=language,
                force_language=force_language,
                model=selected_model,
                temperature=temp_val,
                max_tokens=max_tokens,
            )
            
            # Send response back to client
            await websocket.send_text(json.dumps(chat_response.model_dump()))
            
            # If handover is needed, send Telegram notification
            if chat_response.handover_to_manager:
                await telegram_service.send_handover_notification(
                    chat_request.session_id,
                    chat_request.message,
                    chat_response
                )
                
                # TODO: Update conversation state in database
                # TODO: Log message in database
                
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()
