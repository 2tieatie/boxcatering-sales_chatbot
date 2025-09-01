"""Telegram service for sending notifications."""

from typing import Optional
from telegram import Bot
from loguru import logger

from app.config import settings
from app.schemas.chat import ChatResponse


class TelegramService:
    """Service for sending Telegram notifications."""
    
    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.bot = None
        
        if self.bot_token:
            try:
                self.bot = Bot(token=self.bot_token)
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
    
    async def send_handover_notification(
        self, 
        session_id: str, 
        customer_message: str, 
        chat_response: ChatResponse
    ) -> bool:
        """Send handover notification to Telegram."""
        if not self.bot or not self.chat_id:
            logger.warning("Telegram bot not configured")
            return False
        
        try:
            message = self._format_handover_message(
                session_id, customer_message, chat_response
            )
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"Handover notification sent for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    def _format_handover_message(
        self, 
        session_id: str, 
        customer_message: str, 
        chat_response: ChatResponse
    ) -> str:
        """Format the handover message for Telegram."""
        return f"""
🚨 <b>HANDOVER REQUEST</b>

<b>Session ID:</b> {session_id}
<b>Reason:</b> {chat_response.handover_reason}
<b>Description:</b> {chat_response.handover_reason_description}

<b>Customer Message:</b>
{customer_message}

<b>Bot Response:</b>
{chat_response.response}

<b>Action Required:</b> Please review this conversation and take over if needed.
        """.strip()
