"""Chat WebSocket endpoint."""

from http.client import HTTPException
import json
from datetime import datetime, date, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from loguru import logger
from openai import OpenAI
from app.services.auth_service import AuthService
from app.services.role_service import RoleService
from app.config import settings
from app.database import get_db
from app.services.chatbot_service import ChatbotService
from app.services.telegram_service import TelegramService
from app.schemas.chat import ChatRequest, ChatResponse, SummaryRequest
from app.schemas.order import OrderCreate
from app.models import Order
from app.models import Conversation
from app.models.conversation import HandoverState
from app.models.message import Message, MessageSender, MessageChannel
from app.utils.logging_config import get_logger
from app.utils.utils import format_kyiv_timestamp, parse_delivery_date, parse_bool
from app.models.system_config import SystemConfig
from app.models import Customer

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize services
chatbot_service = ChatbotService()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    app_logger = get_logger("app")
    prompt_logger = get_logger("prompt")

    await websocket.accept()
    app_logger.info("WebSocket connection established")

    try:
        while True:
            data = await websocket.receive_text()
            app_logger.info(f"WebSocket message received: {len(data)} characters")

            chat_data = json.loads(data)
            chat_request = ChatRequest(
                session_id=chat_data.get("session_id"),
                sender=chat_data.get("sender", "user"),
                message=chat_data.get("message"),
                timestamp=datetime.fromisoformat(chat_data.get("timestamp")),
            )

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
                logger.debug(
                    f"Created new conversation for session_id={chat_request.session_id}"
                )



            prompt_logger.info(
                f"WEBSOCKET_CHAT: processing message for conversation {conversation.id}"
            )

            from app.models.chatbot_config import ChatbotConfig

            active_config = (
                db.query(ChatbotConfig).filter(ChatbotConfig.is_active == True).first()
            )

            try:
                config_id_param = websocket.query_params.get("config_id")
            except Exception:
                config_id_param = None
            selected_config = active_config
            if config_id_param is not None:
                try:

                    authz = websocket.headers.get("Authorization") or ""
                    token = authz.split(" ")[1] if " " in authz else authz
                    if not token:
                        try:
                            token = websocket.query_params.get("token") or ""
                        except Exception:
                            token = ""
                    auth_service = AuthService()
                    role_service = RoleService()
                    user = await auth_service.get_current_user(token, db)
                    role_service.require_admin_or_system_admin(user)
                    try:
                        cid = int(config_id_param)
                        manual = (
                            db.query(ChatbotConfig)
                            .filter(ChatbotConfig.id == cid)
                            .first()
                        )
                        if manual is not None:
                            selected_config = manual
                    except Exception:
                        pass
                except Exception:
                    selected_config = active_config

            language = "uk"
            force_language = True

            cfg = {c.key: c.value for c in db.query(SystemConfig).all()}
            selected_model = cfg.get("openai_model") or None
            max_tokens = int(cfg.get("openai_max_tokens") or 0) or None
            try:
                temp_val = (
                    float(cfg.get("openai_temperature"))
                    if cfg.get("openai_temperature") is not None
                    else None
                )
            except Exception:
                temp_val = None

            ctx_enabled = parse_bool(cfg.get("system_context_docs_enabled"))
            ctx_dir = cfg.get("system_context_docs_dir") or None
            try:
                ctx_max_chars = (
                    int(cfg.get("system_context_docs_max_chars"))
                    if cfg.get("system_context_docs_max_chars") is not None
                    else None
                )
            except Exception:
                ctx_max_chars = None

            qs = websocket.query_params
            debug_enabled = str(qs.get("debug", "0")).lower() in {"1", "true", "yes"}

            user_message = Message(
                chat_id=conversation.id,
                sender=MessageSender.USER,
                channel=MessageChannel.WEB,
                text=chat_request.message,
            )
            db.add(user_message)
            db.commit()
            print("USER MESSAGE ADDED")
            conversation_history = chatbot_service.get_conversation_history(
                conversation.id, db
            )

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
                        "system_instruction": selected_config.system_instruction,
                        "id": selected_config.id,
                    }
                    if selected_config
                    else None
                ),
                conversation_history=conversation_history,
            )
            bot_message = Message(
                chat_id=conversation.id,
                sender=MessageSender.BOT,
                channel=MessageChannel.WEB,
                text=chat_response.response,
            )
            db.add(bot_message)
            db.commit()
            print("BOT MESSAGE ADDED")

            db.refresh(bot_message)
            try:
                should_log = True
                if active_config and active_config.conversation_logging is not None:
                    should_log = bool(active_config.conversation_logging)
                if should_log:
                    visible_text = str(chat_response.response or "")
                    try:
                        last_open = visible_text.rfind("{")
                        last_close = visible_text.rfind("}")
                        if (
                            last_open != -1
                            and last_close != -1
                            and last_close > last_open
                        ):
                            candidate = visible_text[last_open : last_close + 1]
                            try:
                                json.loads(candidate)
                                visible_text = visible_text[:last_open].rstrip()
                            except Exception:
                                pass
                    except Exception:
                        pass

                if chat_response.handover_to_manager:
                    if conversation.handover_state not in {
                        HandoverState.HANDOVER_IN_PROGRESS
                    }:
                        conversation.handover_state = HandoverState.HANDOVER_PENDING
                    conversation.handover_reason = (
                        (
                            chat_response.handover_reason.value
                            if hasattr(chat_response.handover_reason, "value")
                            else str(chat_response.handover_reason)
                        )
                        if chat_response.handover_reason is not None
                        else conversation.handover_reason
                    )
                    conversation.handover_reason_description = (
                        chat_response.handover_reason_description
                        or conversation.handover_reason_description
                    )
                else:
                    if conversation.handover_state in {None, HandoverState.NONE}:
                        conversation.handover_state = HandoverState.NONE

                db.commit()
                db.refresh(conversation)
            except Exception as save_err:
                db.rollback()
                logger.error(
                    f"Failed to save bot message or update conversation: {save_err}"
                )

            print(f"{chat_response=}")
            try:
                if chat_response.action == "create_order" and isinstance(
                    chat_response.data, dict
                ):
                    payload = chat_response.data
                    if (
                        "conversation_id" not in payload
                        or payload.get("conversation_id") is None
                    ):
                        payload["conversation_id"] = conversation.id

                    normalized_delivery_date = parse_delivery_date(
                        payload.get("delivery_date")
                    )
                    order_create = OrderCreate(
                        customer_id=(
                            int(payload["customer_id"])
                            if payload.get("customer_id") is not None
                            else None
                        ),
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
                        guests_count=payload.get("guests_count"),
                        priority=payload.get("priority"),
                    )

                    today_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
                    base_prefix = f"ORD-{today_prefix}-"
                    last = (
                        db.query(Order)
                        .filter(Order.order_number.like(f"{base_prefix}%"))
                        .order_by(Order.id.desc())
                        .first()
                    )
                    try:
                        last_seq = (
                            int((last.order_number or "").split("-")[-1]) if last else 0
                        )
                    except Exception:
                        last_seq = 0
                    next_seq = last_seq + 1
                    order_number = f"{base_prefix}{next_seq:04d}"

                    customer_id = order_create.customer_id
                    if customer_id is None:

                        customer = None
                        if order_create.customer_email:
                            customer = (
                                db.query(Customer)
                                .filter(Customer.email == order_create.customer_email)
                                .first()
                            )
                        if not customer and order_create.customer_phone:
                            customer = (
                                db.query(Customer)
                                .filter(Customer.phone == order_create.customer_phone)
                                .first()
                            )
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
                            raise ValueError(
                                "Customer info is required to create an order"
                            )
                        customer_id = customer.id
                    else:
                        customer = (
                            db.query(Customer)
                            .filter(Customer.id == customer_id)
                            .first()
                        )
                    new_address = (order_create.customer_address or "").strip()
                    if customer and new_address:
                        current_address = (customer.address or "").strip()
                        if current_address != new_address:
                            customer.address = new_address
                            db.commit()
                            db.refresh(customer)
                    new_order = Order(
                        order_number=order_number,
                        customer_id=customer_id,
                        conversation_id=order_create.conversation_id,
                        state=order_create.state or getattr(Order, "state").default.arg,
                        total_amount=order_create.total_amount or 0,
                        currency=order_create.currency or "UAH",
                        notes=order_create.notes or "",
                        delivery_date=order_create.delivery_date,
                        delivery_time=order_create.delivery_time,
                        delivery_address=order_create.customer_address,
                        menu_items=order_create.menu_items,
                    )
                    db.add(new_order)
                    telegram_service = TelegramService(
                        bot_token=cfg.get("telegram_bot_token"),
                        chat_id=cfg.get("telegram_chat_id"),
                    )

                    try:
                        if (
                            conversation
                            and (conversation.customer_id is None)
                            and customer_id
                        ):
                            conversation.customer_id = customer_id
                    except Exception:
                        pass
                    db.commit()
                    db.refresh(new_order)
                    await telegram_service.send_new_order_notification(new_order, customer)
                    resp_dict = chat_response.model_dump()
                    data = dict(resp_dict.get("data") or {})
                    data.update(
                        {
                            "order_id": new_order.id,
                            "order_number": new_order.order_number,
                        }
                    )
                    resp_dict["data"] = data
                    await websocket.send_text(json.dumps(resp_dict))
                else:
                    await websocket.send_text(json.dumps(chat_response.model_dump()))
            except Exception as action_err:
                db.rollback()
                logger.error(f"Failed to execute chat action: {action_err}")
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

                try:
                    notif_pref = (
                        str(cfg.get("telegram_notifications") or "").strip().lower()
                    )
                except Exception:
                    notif_pref = ""
                if notif_pref in {"all", "errors"}:
                    telegram_service = TelegramService(
                        bot_token=cfg.get("telegram_bot_token"),
                        chat_id=cfg.get("telegram_chat_id"),
                    )
                    await telegram_service.send_error_notification(
                        chat_request.session_id,
                        f"Order action failed: {action_err}",
                    )

            try:
                notif_pref = (
                    str(cfg.get("telegram_notifications") or "").strip().lower()
                )
            except Exception:
                notif_pref = ""
            should_notify_handover = notif_pref in {"all", "handovers"}

            if chat_response.handover_to_manager and should_notify_handover:
                payload = chat_response.data
                customer_id = (
                    int(payload["customer_id"])
                    if payload.get("customer_id") is not None
                    else None
                )
                customer_phone = payload.get("customer_phone")
                customer_name = payload.get("customer_name")
                customer = None
                if not customer and customer_phone:
                    customer = (
                        db.query(Customer)
                        .filter(Customer.phone == customer_phone)
                        .first()
                    )
                elif not customer and customer_name:
                    customer = Customer(
                        name=customer_name,
                        phone=customer_phone,
                    )
                    db.add(customer)
                    db.commit()
                    db.refresh(customer)
                telegram_service = TelegramService(
                    bot_token=cfg.get("telegram_bot_token"),
                    chat_id=cfg.get("telegram_chat_id"),
                )
                await telegram_service.send_handover_notification(
                    chat_request.session_id, chat_request.message, chat_response
                )

            prompt_logger.info(
                f"WEBSOCKET_RESPONSE: sent response to conversation {conversation.id}"
            )

    except WebSocketDisconnect:
        app_logger.info("WebSocket connection closed")
    except Exception as e:
        app_logger.error(f"WebSocket error: {str(e)}")

        try:
            notif_pref = (
                str((locals().get("cfg") or {}).get("telegram_notifications") or "")
                .strip()
                .lower()
            )
        except Exception:
            notif_pref = ""
        if notif_pref in {"all", "errors"}:
            try:
                await telegram_service.send_error_notification(
                    None, f"WebSocket error: {e}"
                )
            except Exception:
                pass

        await websocket.close()


@router.post("/summary", response_model=str)
async def update_summary(
    payload: SummaryRequest,
    db: Session = Depends(get_db),
):
    """Get conversation summary."""
    logger.info(f"Generating summary for conversation {payload}")
    conversation_id = payload.conversation_id
    mappedMessages = payload.mappedMessages

    api_key = settings.openai_api_key
    model = settings.openai_model

    client = OpenAI(api_key=api_key)

    # Create the chat completion
    request_kwargs = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Згенеруй підсумок діалогу, вказавши, що замовив клієнт із деталями по його замовленню (дата, час, каталог, інформацію про доставку, контактні дані):\n"
                    f"{mappedMessages}"
                ),
            }
        ],
    }

    response = client.chat.completions.create(**request_kwargs)
    ai_response = response.choices[0].message.content or ""
    logger.info(f"Generated summary: {ai_response}")

    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.summary = ai_response

    db.commit()
    db.refresh(conversation)

    return ai_response or ""
