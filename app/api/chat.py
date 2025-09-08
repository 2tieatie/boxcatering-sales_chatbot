"""Chat WebSocket endpoint."""

import json
from datetime import datetime, date, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.services.chatbot_service import ChatbotService
from app.services.telegram_service import TelegramService
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.order import OrderCreate
from app.models import Order
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
            
            # Load OpenAI and system settings from system configs if present
            from app.models.system_config import SystemConfig
            cfg = {c.key: c.value for c in db.query(SystemConfig).all()}
            selected_model = cfg.get("openai_model") or None
            max_tokens = int(cfg.get("openai_max_tokens") or 0) or None
            try:
                temp_val = float(cfg.get("openai_temperature")) if cfg.get("openai_temperature") is not None else None
            except Exception:
                temp_val = None

            # Context documents runtime overrides
            def parse_bool(v):
                if v is None:
                    return None
                if isinstance(v, bool):
                    return v
                s = str(v).lower().strip()
                return s in {"1", "true", "yes", "on"}

            ctx_enabled = parse_bool(cfg.get("system_context_docs_enabled"))
            ctx_dir = cfg.get("system_context_docs_dir") or None
            try:
                ctx_max_chars = int(cfg.get("system_context_docs_max_chars")) if cfg.get("system_context_docs_max_chars") is not None else None
            except Exception:
                ctx_max_chars = None

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

            # Get conversation history for context
            conversation_history = chatbot_service.get_conversation_history(conversation.id, db)
            
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
                        # Context docs overrides
                        "context_docs_enabled": ctx_enabled if ctx_enabled is not None else None,
                        "context_docs_dir": ctx_dir,
                        "context_docs_max_chars": ctx_max_chars,
                    }
                    if active_config
                    else None
                ),
                conversation_history=conversation_history,
            )
            
            # Persist bot response and update conversation state
            try:
                should_log = True
                if active_config and active_config.conversation_logging is not None:
                    should_log = bool(active_config.conversation_logging)
                if should_log:
                    # Sanitize customer-visible text to avoid leaking JSON action payloads
                    visible_text = str(chat_response.response or "")
                    try:
                        # Remove any trailing JSON block if accidentally appended by the model
                        # Keep everything before the last balanced JSON object marker
                        last_open = visible_text.rfind("{")
                        last_close = visible_text.rfind("}")
                        if last_open != -1 and last_close != -1 and last_close > last_open:
                            candidate = visible_text[last_open:last_close + 1]
                            # Try to parse to confirm it's JSON; if yes, strip it from visible text
                            try:
                                json.loads(candidate)
                                visible_text = visible_text[:last_open].rstrip()
                            except Exception:
                                pass
                    except Exception:
                        pass

                    bot_message = Message(
                        chat_id=conversation.id,
                        sender=MessageSender.BOT,
                        channel=MessageChannel.WEB,
                        text=visible_text,
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

            # If AI requested an actionable task, execute it before replying
            try:
                if chat_response.action == "create_order" and isinstance(chat_response.data, dict):
                    # Minimal mapping: require customer_id; optional conversation link
                    payload = chat_response.data
                    # Attach conversation id if not provided
                    if "conversation_id" not in payload or payload.get("conversation_id") is None:
                        payload["conversation_id"] = conversation.id

                    # Helpers to parse and normalize incoming data
                    def parse_delivery_date(value):
                        if value is None:
                            return None
                        if isinstance(value, datetime):
                            return value
                        if isinstance(value, date):
                            return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
                        if isinstance(value, str):
                            value = value.strip()
                            # Try ISO first
                            for fmt in ("%Y-%m-%d", "%Y.%m.%d"):
                                try:
                                    dt = datetime.strptime(value, fmt)
                                    return dt.replace(tzinfo=timezone.utc)
                                except Exception:
                                    pass
                            # Try common European formats like DD.MM.YYYY and DD/MM/YYYY
                            for fmt in ("%d.%m.%Y", "%d/%m/%Y"):
                                try:
                                    dt = datetime.strptime(value, fmt)
                                    return dt.replace(tzinfo=timezone.utc)
                                except Exception:
                                    pass
                        return None

                    normalized_delivery_date = parse_delivery_date(payload.get("delivery_date"))

                    # Coerce/validate fields accepted by OrderCreate
                    order_create = OrderCreate(
                        customer_id=(int(payload["customer_id"]) if payload.get("customer_id") is not None else None),
                        customer_name=payload.get("customer_name"),
                        customer_email=payload.get("customer_email"),
                        customer_phone=payload.get("customer_phone"),
                        customer_address=payload.get("customer_address"),
                        delivery_date=normalized_delivery_date,
                        delivery_time=payload.get("delivery_time"),
                        menu_items=payload.get("menu_items"),
                        conversation_id=payload.get("conversation_id"),
                        state=payload.get("state"),
                        total_amount=payload.get("total_amount"),
                        currency=payload.get("currency"),
                        notes=payload.get("notes"),
                    )

                    # Generate an order number similarly to POST /orders
                    today_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
                    base_prefix = f"ORD-{today_prefix}-"
                    last = (
                        db.query(Order)
                        .filter(Order.order_number.like(f"{base_prefix}%"))
                        .order_by(Order.id.desc())
                        .first()
                    )
                    try:
                        last_seq = int((last.order_number or "").split("-")[-1]) if last else 0
                    except Exception:
                        last_seq = 0
                    next_seq = last_seq + 1
                    order_number = f"{base_prefix}{next_seq:04d}"

                    # Resolve or create customer if needed (reuse logic similar to POST /orders)
                    customer_id = order_create.customer_id
                    if customer_id is None:
                        from app.models import Customer
                        customer = None
                        if order_create.customer_email:
                            customer = db.query(Customer).filter(Customer.email == order_create.customer_email).first()
                        if not customer and order_create.customer_phone:
                            customer = db.query(Customer).filter(Customer.phone == order_create.customer_phone).first()
                        if not customer and order_create.customer_name:
                            customer = Customer(
                                name=order_create.customer_name,
                                email=order_create.customer_email,
                                phone=order_create.customer_phone,
                                address=order_create.customer_address,
                            )
                            db.add(customer)
                            db.commit()
                            db.refresh(customer)
                        if not customer:
                            raise ValueError("Customer info is required to create an order")
                        customer_id = customer.id

                    new_order = Order(
                        order_number=order_number,
                        customer_id=customer_id,
                        conversation_id=order_create.conversation_id,
                        state=order_create.state or getattr(Order, 'state').default.arg,
                        total_amount=order_create.total_amount or 0,
                        currency=order_create.currency or "UAH",
                        notes=order_create.notes,
                        delivery_date=order_create.delivery_date,
                        delivery_time=order_create.delivery_time,
                        menu_items=order_create.menu_items,
                    )
                    db.add(new_order)
                    # Ensure conversation is linked to this customer for cross-linking in UI
                    try:
                        if conversation and (conversation.customer_id is None) and customer_id:
                            conversation.customer_id = customer_id
                    except Exception:
                        pass
                    db.commit()
                    db.refresh(new_order)

                    # Augment response with created order id/number for the frontend
                    resp_dict = chat_response.model_dump()
                    data = dict(resp_dict.get("data") or {})
                    data.update({"order_id": new_order.id, "order_number": new_order.order_number})
                    resp_dict["data"] = data
                    await websocket.send_text(json.dumps(resp_dict))
                else:
                    # Send response back to client
                    await websocket.send_text(json.dumps(chat_response.model_dump()))
            except Exception as action_err:
                db.rollback()
                logger.error(f"Failed to execute chat action: {action_err}")
                # Send a clear error message back to user instead of a false confirmation
                error_msg = (
                    "Не вдалося створити замовлення: перевірте дату доставки у форматі YYYY-MM-DD, "
                    "або надайте коректні дані і спробуйте ще раз."
                )
                fallback = {
                    "response": error_msg,
                    "handover_to_manager": False,
                    "debug": {"error": str(action_err)} if debug_enabled else None,
                }
                await websocket.send_text(json.dumps(fallback))

                # Notify errors to Telegram when configured
                try:
                    notif_pref = str(cfg.get("telegram_notifications") or "").strip().lower()
                except Exception:
                    notif_pref = ""
                if notif_pref in {"all", "errors"}:
                    await telegram_service.send_error_notification(
                        chat_request.session_id,
                        f"Order action failed: {action_err}",
                    )
            
            # If handover is needed, send Telegram notification based on settings
            try:
                notif_pref = str(cfg.get("telegram_notifications") or "").strip().lower()
            except Exception:
                notif_pref = ""
            should_notify_handover = notif_pref in {"all", "handovers"}
            if chat_response.handover_to_manager and should_notify_handover:
                await telegram_service.send_handover_notification(
                    chat_request.session_id,
                    chat_request.message,
                    chat_response
                )
                
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        # Attempt to notify on generic WebSocket-level errors when configured
        try:
            # cfg might not be available if error happens very early; guard usage
            notif_pref = str((locals().get("cfg") or {}).get("telegram_notifications") or "").strip().lower()
        except Exception:
            notif_pref = ""
        if notif_pref in {"all", "errors"}:
            try:
                await telegram_service.send_error_notification(None, f"WebSocket error: {e}")
            except Exception:
                pass
        await websocket.close()
