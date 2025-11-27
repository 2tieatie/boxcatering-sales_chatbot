"""Telegram service for sending notifications."""

from typing import Optional
from zoneinfo import ZoneInfo

from telegram import Bot
from loguru import logger

from app.config import settings
from app.models import Order, Customer
from app.schemas import OrderCreate
from app.schemas.chat import ChatResponse


class TelegramService:
    """Service for sending Telegram notifications."""

    def __init__(self, bot_token: str, chat_id: int):
        self.bot_token = bot_token or settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id
        self.bot = None

        if self.bot_token:
            try:
                self.bot = Bot(token=self.bot_token)
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")

    async def send_handover_notification(
        self, session_id: str, customer_message: str, chat_response: ChatResponse
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
                chat_id=self.chat_id, text=message, parse_mode="HTML"
            )

            logger.info(f"Handover notification sent for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    async def send_new_order_notification(
        self, order: Order, customer: Customer
    ) -> bool:
        """Send new order notification to Telegram."""
        if not self.bot or not self.chat_id:
            logger.warning("Telegram bot not configured")
            return False

        try:
            message = self._format_order_message(order, customer)

            await self.bot.send_message(
                chat_id=self.chat_id, text=message, parse_mode="HTML"
            )

            logger.info(f"Sent new order notification for OID: {order.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False


    async def send_error_notification(
        self,
        session_id: Optional[str],
        error_message: str,
    ) -> bool:
        """Send an error notification to Telegram if configured.

        Returns True on successful send, False otherwise.
        """
        if not self.bot or not self.chat_id:
            logger.warning("Telegram bot not configured for error notifications")
            return False

        try:
            text = (
                f"\u26A0\uFE0F <b>ERROR</b>\n\n"
                f"<b>Session ID:</b> {session_id or '-'}\n"
                f"<b>Details:</b> {error_message}"
            )
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram error notification: {e}")
            return False

    def _format_handover_message(
        self, session_id: str, customer_message: str, chat_response: ChatResponse
    ) -> str:
        """Format the handover message for Telegram."""
        return f"""
🚨 <b>HANDOVER REQUEST</b>

<b>Session ID:</b> {session_id}
<b>Reason:</b> {chat_response.handover_reason}
<b>Description:</b> {chat_response.handover_reason_description}

<b>Customer:</b> <code>{chat_response.data.get("name", chat_response.data.get("customer_name", "Не вказане Імʼя"))}, {chat_response.data.get("phone", chat_response.data.get("customer_phone", "Не вказаний Номер"))}</code>

<b>Customer Message:</b>
{customer_message}

<b>Bot Response:</b>
{chat_response.response}

<b>Action Required:</b> Please review this conversation and take over if needed.
""".strip()


    def _format_order_message(
        self, order: Order, customer: Customer
    ) -> str:
        """Format the order message for Telegram."""
        return f"""
<b>📅 {order.created_at.astimezone(ZoneInfo("Europe/Kyiv")).strftime("%Y-%m-%d %H:%M")}</b>
<b>🆕 Нове замовлення</b>
<b>👤 Ім'я:</b> {customer.name} 
<b>📞 Телефон:</b> {customer.phone}

<b>🚚 Тип доставки:</b> ДОСТАВКА
<b>🕓 Дата-час доставки:</b> {order.delivery_date.strftime("%Y-%m-%d")} {order.delivery_time}
<b>📍 Адреса:</b> {order.delivery_address}

<b>Склад замовлення:</b>
{order.menu_items}

<b>💰 Кінцева ціна: {order.total_amount}</b> грн.
""".strip()