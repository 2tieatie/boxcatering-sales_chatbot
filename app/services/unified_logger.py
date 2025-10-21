from typing import Dict, Any, Optional
from loguru import logger
from app.database import get_db
from app.models.prompt_log import PromptLog
from app.utils.logging_config import get_logger


class UnifiedLogger:
    def __init__(self):
        self.prompt_logger = get_logger("prompt")
        self.app_logger = get_logger("app")
    
    def log_chat_request(self, correlation_id: str, data: Dict[str, Any]):
        # File logging
        self.prompt_logger.info(f"[{correlation_id}] CHAT_REQUEST: {data}")
        
        # Console logging (for development)
        logger.info(f"[{correlation_id}] Chat request: {data.get('user_message', '')[:50]}...")
    
    def log_chat_response(self, correlation_id: str, data: Dict[str, Any]):
        # File logging
        self.prompt_logger.info(f"[{correlation_id}] CHAT_RESPONSE: {data}")
        
        # Console logging
        logger.info(f"[{correlation_id}] Chat response: {data.get('response_length', 0)} chars")
    
    def log_to_database(self, correlation_id: str, data: Dict[str, Any]):
        """Log prompt data to database for querying via /prompts endpoint."""
        try:
            db = next(get_db())
            
            # Map data dictionary to PromptLog fields
            db_log = PromptLog(
                correlation_id=correlation_id,
                user_id=data.get("user_id"),
                conversation_id=data.get("conversation_id"),
                config_id=data.get("config_id"),
                model=data.get("model"),
                system_prompt_hash=data.get("system_prompt_hash"),
                system_prompt_preview=data.get("system_prompt_preview"),
                system_prompt_length=data.get("system_prompt_length"),
                prompt_trace_json=data.get("prompt_trace_json"),
                user_message=data.get("user_message"),
                request_json=data.get("request_json"),
                response_json=data.get("response_json"),
                duration_ms=data.get("duration_ms"),
                error=data.get("error"),
            )
            
            db.add(db_log)
            db.commit()
            
            # Log successful database write
            self.app_logger.info(f"[{correlation_id}] Database log written successfully")
            
        except Exception as e:
            self.app_logger.warning(f"[{correlation_id}] Failed to write to database: {e}")
            logger.warning(f"Failed to write to database: {e}")
