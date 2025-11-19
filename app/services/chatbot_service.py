import asyncio
import pprint
from datetime import date, datetime, timedelta
import re
import json
import csv
import hashlib
from sqlite3 import IntegrityError
import time
import uuid

from pathlib import Path
from typing import Optional, Dict, Any, List
from langchain_qdrant import QdrantVectorStore
from langchain.tools import tool
from langchain_core.messages import (
    SystemMessage,
    AIMessage,
    HumanMessage,
    ToolMessage,
    BaseMessage,
)
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI
from loguru import logger
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

from app.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, HandoverReason
from app.services.prompts.assortement_agent import assortment_system_message
from app.services.prompts.delivery_agent import delivery_agent_system
from app.services.prompts.main_agent import main_agent_system
from app.services.prompts.validation_agent import validation_system_message
from app.services.tools.geocoding import get_delivery_price_tool
from app.services.tools.products import get_products_tool
from app.services.unified_logger import UnifiedLogger
from haystack.utils import Secret
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from app.utils.logging_config import get_logger

prompt_logger = get_logger("prompt")

def _model_supports_temperature(model_name: str) -> bool:
    unsupported = {"gpt-5", "gpt-5-mini", "gpt-5-nano"}
    return model_name not in unsupported

def _model_supports_reasoning(model_name: str) -> bool:
    supported = {"gpt-5", "gpt-5-mini", "gpt-5-nano"}
    return model_name in supported

class Agent:
    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        tools: List[BaseTool] | None = None,
        enable_memory: bool = True,
        temperature: float = 0.7,
        model: str = "gpt-5",
    ):
        self.name = name
        self.description = description
        self.tools: List[BaseTool] = tools or []
        self.enable_memory = enable_memory
        self.memory: List[BaseMessage] = []
        self.model = ChatOpenAI(
            model=model,
            temperature=temperature if _model_supports_temperature(model) else None,
            api_key=settings.openai_api_key,
            reasoning={
                "effort": "low",
                "summary": None,
            } if _model_supports_reasoning(model) else None,
        )
        self.model.bind_tools(self.tools)
        self.system_message = system_message

    async def run_tool(self, tool_name: str, **kwargs: Any) -> Any:
        if tool_name not in [t.name for t in self.tools]:
            raise PermissionError(
                f"Agent '{self.name}' is not allowed to call tool '{tool_name}'"
            )
        # logger.info(f"[{self.name}] → tool call: {tool_name} | payload={kwargs}")
        prompt_logger.info(f"[{self.name}] → tool call: {tool_name} | payload={kwargs}")

        for t in self.tools:
            if t.name == tool_name:
                if hasattr(t, "ainvoke"):
                    result = await t.ainvoke(kwargs)
                else:
                    result = await asyncio.to_thread(t.invoke, **kwargs)
                return result
        raise ValueError(f"Unknown tool '{tool_name}'")

    def build_messages(self, query: str) -> List[BaseMessage]:
        messages: List[BaseMessage] = [SystemMessage(content=self.system_message)]

        if self.enable_memory and self.memory:
            messages.extend(self.memory)

        messages.append(HumanMessage(content=query))
        return messages

    async def execute(self, query_or_messages: List[BaseMessage] | str) -> Any:
        if isinstance(query_or_messages, str):
            messages: List[BaseMessage] = self.build_messages(query_or_messages)
        else:
            messages = list(query_or_messages)
            system_messages = list(
                filter(lambda m: isinstance(m, SystemMessage), messages)
            )
            if not system_messages:
                messages = [SystemMessage(content=self.system_message), *messages]
        if self.enable_memory:
            self.memory = list(messages)
        # logger.info(f"[{self.name}] {self.memory=}")
        last_tool_results: Dict[str, Any] = {}

        while True:
            # logger.info(f"[{self.name}] executing, messages_count={len(messages)}")
            prompt_logger.info(f"[{self.name}] executing, messages_count={len(messages)}")
            bound_model = self.model.bind_tools(self.tools)
            msg = await bound_model.ainvoke(messages)

            # logger.info(f"[{self.name}] msg: {msg}")
            prompt_logger.info(f"[{self.name}] msg: {msg}")

            tool_calls = msg.tool_calls
            # logger.info(f"[{self.name}] tool_calls: {tool_calls}")
            prompt_logger.info(f"[{self.name}] tool_calls: {tool_calls}")
            messages.append(msg)

            if tool_calls:

                async def execute_single_tool(call):
                    args = call["args"]
                    if isinstance(args, str):
                        try:
                            payload = json.loads(args)
                        except Exception:
                            payload = {}
                    else:
                        payload = args

                    tool_name = call["name"]
                    tool_call_id = call["id"]

                    result = await self.run_tool(tool_name, **payload)
                    last_tool_results[tool_call_id] = result

                    try:
                        content = json.dumps(result, ensure_ascii=False)
                    except TypeError:
                        content = str(result)

                    tool_message = ToolMessage(
                        content=content,
                        name=tool_name,
                        tool_call_id=tool_call_id,
                    )
                    return tool_message

                tool_messages = await asyncio.gather(
                    *[execute_single_tool(call) for call in tool_calls]
                )

                # logger.info(f"[{self.name}] tool_messages: {tool_messages}")
                prompt_logger.info(f"[{self.name}] tool_messages: {tool_messages}")
                messages.extend(tool_messages)

                if self.enable_memory:
                    self.memory = list(messages)

                continue

            if self.enable_memory:
                self.memory = list(messages)

            if isinstance(msg.content, list):
                return list(
                    filter(lambda m: m.get("type") != "reasoning", msg.content)
                )[0]["text"]
            return msg.content

    def as_tool(self) -> BaseTool:
        class AgentInput(BaseModel):
            query: str = Field(
                ..., description="The task that this agent should solve end-to-end."
            )

        async def _entry(query: str) -> Any:
            # logger.info(f"[{self.name}] entrypoint tool → execute")
            prompt_logger.info(f"[{self.name}] entrypoint tool → execute")
            return await self.execute(query)

        return StructuredTool(
            name=self.name,
            description=self.description,
            args_schema=AgentInput,
            coroutine=_entry,
        )


def get_main_agent() -> Agent:
    assortment_agent = Agent(
        "assortment_agent",
        description="Specialized menu agent. Identifies event format (buffet/coffee-break/cocktail; banquet→escalate), collects guest_count + event_duration.",
        system_message=assortment_system_message,
        enable_memory=True,
        tools=[get_products_tool],
        model="gpt-4.1"
    )

    delivery_agent = Agent(
        "delivery_agent",
        description="Delivery time validation specialist. Informs customer of working hours (09:00-19:00, 7 days/week). Collects desired delivery date (handles relative: сьогодні/завтра, explicit: DD.MM) + exact time. Normalizes input to YYYY-MM-DD and HH:MM format. Calls get_date_time(query) returning {valid, approved_time, approved_date, reason_if_invalid}. Enforces: working window 09:00-19:00, 2h lead time for TODAY only (tomorrow+ no lead check). NO autocompletion or nearest-time suggestions. Accepts/rejects exactly as requested.",
        system_message=delivery_agent_system,
        tools=[get_delivery_price_tool],
        enable_memory=True,
        model="gpt-4.1-mini"
    )
    validation_agent = Agent(
        "validation_agent",
        description="Contact data validation specialist. Validates customer_name (2-40 chars, letters only, Cyrillic/Latin OK) and customer_phone (0XXXXXXXXX/380XXXXXXXXX/+380XXXXXXXXX). Strict rules, no flexibility. Returns: customer_name, customer_phone (normalized).",
        system_message=validation_system_message,
        tools=[],
        enable_memory=True,
        model="gpt-4.1-mini"
    )

    validation_agent_tool = validation_agent.as_tool()
    delivery_agent_tool = delivery_agent.as_tool()
    assortment_agent_tool = assortment_agent.as_tool()

    main_agent = Agent(
        "top_agent",
        description="",
        system_message=main_agent_system,
        tools=[validation_agent_tool, delivery_agent_tool, assortment_agent_tool],
        enable_memory=True,
        model="gpt-5.1"
    )
    return main_agent


class ChatbotService:
    def __init__(self):
        api_key = settings.openai_api_key
        model = "gpt-4o mini"

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self._context_docs_cache: Dict[str, str] = {}
        self.document_store = QdrantDocumentStore(
            url="https://0a87a722-2e15-4fc0-aa39-5c99fc2866ca.us-west-1-0.aws.cloud.qdrant.io:6333",
            api_key=Secret.from_token(
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.DI_UrA1AMY62uHlhTsWxIwhsdtyGU0KU2oiwY5e43Vc"
            ),
            index="products",
            embedding_dim=1536,
            recreate_index=False,
        )
        self.openai_api_key = api_key
        self.unified_logger = UnifiedLogger()

    async def process_message(
        self,
        chat_request: ChatRequest,
        language: str = "uk",
        force_language: bool = True,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        debug: bool = False,
        config: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[list] = None,
    ) -> ChatResponse:
        try:
            start_time = time.perf_counter()

            correlation_id = str(uuid.uuid4())[:8]

            self.unified_logger.log_chat_request(
                correlation_id,
                {
                    "user_message": chat_request.message,
                    "language": language,
                    "model": model or self.model,
                    "conversation_history_length": (
                        len(conversation_history) if conversation_history else 0
                    ),
                },
            )

            messages = []
            if conversation_history:
                for msg in conversation_history[-13:]:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        if msg["role"] == "assistant":
                            messages.append(AIMessage(content=msg["content"]))
                        elif msg["role"] == "user":
                            messages.append(HumanMessage(content=msg["content"]))

            messages.append(HumanMessage(content=chat_request.message))

            agent = get_main_agent()
            ai_response = await agent.execute(messages)
            parsed_response = self._parse_ai_response(ai_response)
            user_text = (parsed_response.get("response") or ai_response or "").strip()
            needs_handover = bool(parsed_response.get("handover_to_manager", False))
            handover_reason = parsed_response.get("handover_reason")
            handover_desc = parsed_response.get("handover_reason_description")
            summary = parsed_response.get("debug", {}).get("summary")
            default_fallback = (config or {}).get("fallback_message") or (
                "Перепрошую, я не зовсім зрозуміла. Будь ласка, перефразуйте, я залюбки допоможу."
            )
            default_handover_msg = (config or {}).get("handover_message") or (
                "Вибачте, я не маю потрібної інформації. Передаю запит менеджеру."
            )

            if not user_text:
                allow_handover = bool((config or {}).get("manager_handover", True))
                if allow_handover:
                    return ChatResponse(
                        response=default_handover_msg,
                        handover_to_manager=True,
                        handover_reason=HandoverReason.OUT_OF_SCOPE,
                        handover_reason_description=(
                            handover_desc or "Model returned empty response"
                        ),
                        summary=summary,
                        debug=(
                            {
                                "model": model or self.model,
                                "temperature": temperature,
                                "reason": "empty_text_fallback",
                            }
                            if debug
                            else None
                        ),
                    )
                return ChatResponse(
                    response=default_fallback,
                    handover_to_manager=False,
                    handover_reason=None,
                    handover_reason_description=(
                        handover_desc or "Model returned empty response"
                    ),
                    debug=(
                        {
                            "model": model or self.model,
                            "temperature": temperature,
                            "reason": "empty_text_no_handover",
                        }
                        if debug
                        else None
                    ),
                )

            if needs_handover and not (parsed_response.get("response") or "").strip():
                user_text = default_handover_msg
                if not handover_reason:
                    handover_reason = HandoverReason.OUT_OF_SCOPE
                if not handover_desc:
                    handover_desc = "Handover requested without a user message"

            if needs_handover and not bool(
                (config or {}).get("manager_handover", True)
            ):
                needs_handover = False
                if not user_text:
                    user_text = default_fallback

            action = None
            data = None
            try:
                if isinstance(parsed_response, dict):
                    action = parsed_response.get("action")
                    payload = parsed_response.get("data")
                    if action and isinstance(payload, dict):
                        data = payload
                    if not action and "create_order" in parsed_response:
                        action = "create_order"
                        maybe_payload = parsed_response.get("create_order")
                        if isinstance(maybe_payload, dict):
                            data = maybe_payload
            except Exception:
                action = None
                data = None

            if action == "create_order":
                try:
                    valid, missing_fields = self._is_valid_order_payload(data)
                except Exception:
                    valid, missing_fields = False, [
                        "menu_items",
                        "delivery_date",
                        "customer_name",
                        "customer_phone",
                        "customer_address",
                    ]

                if not valid:
                    user_text = self._compose_missing_order_details_prompt(
                        language=language, missing_fields=missing_fields
                    )
                    action = None
                    data = None

            chat_result = ChatResponse(
                response=user_text,
                handover_to_manager=needs_handover,
                handover_reason=handover_reason,
                handover_reason_description=handover_desc,
                action=action,
                data=data,
                debug=(
                    {
                        "model": model or self.model,
                        "temperature": temperature,
                        "handover": needs_handover,
                        **({"action": action} if action else {}),
                    }
                    if debug
                    else None
                ),
            )

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            self.unified_logger.log_chat_response(
                correlation_id,
                {
                    "parsed_response": parsed_response,
                    "response": user_text,
                    "response_length": len(user_text),
                    "handover": needs_handover,
                    "handover_reason": handover_reason,
                    "handover_reason_description": handover_desc,
                    "conversation_summary": summary,
                    "action": action,
                    "total_duration": duration_ms,
                },
            )

            try:
                duration_ms = int((time.perf_counter() - start_time) * 1000)

                log_data = {
                    "user_id": None,
                    "conversation_id": None,
                    "config_id": config.get("id") if isinstance(config, dict) else None,
                    "model": model or self.model,
                    "user_message": chat_request.message,
                    "response_json": json.dumps(
                        {
                            "content": ai_response,
                        },
                        ensure_ascii=False,
                    )[:4000],
                    "duration_ms": duration_ms,
                    "error": None,
                }

                self.unified_logger.log_to_database(correlation_id, log_data)

            except Exception as log_err:
                self.unified_logger.app_logger.warning(
                    f"[{correlation_id}] Failed to write prompt log: {log_err}"
                )
                logger.warning(f"Failed to write prompt log: {log_err}")

            return chat_result

        except Exception as e:
            self.unified_logger.app_logger.error(
                f"[{correlation_id}] CHAT_ERROR: {str(e)}"
            )
            logger.error(f"Error processing message: {e}")

            return ChatResponse(
                response=(
                    "Перепрошую, але в мене виникли технічні проблеми. Будь ласка, спробуйте пізніше."
                ),
                handover_to_manager=True,
                handover_reason=HandoverReason.TECH_OR_FINANCIAL_LIMITATION,
                handover_reason_description="Technical error in AI service",
            )

    def _build_system_prompt(*args, **kwargs): ...

    def _parse_ai_response(self, response: str) -> dict:
        try:
            if response.strip().startswith("{"):
                return json.loads(response)
        except Exception:
            pass

        try:
            text = response or ""
            brace_positions: list[int] = [i for i, ch in enumerate(text) if ch == "{"]
            for start in brace_positions:
                candidate = text[start:].strip()
                if not candidate or not candidate.startswith("{"):
                    continue
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and (
                        "action" in parsed
                        or "handover_to_manager" in parsed
                        or "response" in parsed
                    ):
                        return parsed
                except Exception:
                    continue
        except Exception:
            pass

        return {"response": response, "handover_to_manager": False}

    def _is_valid_order_payload(self, data: Optional[dict]) -> tuple[bool, list[str]]:
        """Validate the create_order payload and return validity and missing fields.

        Args:
            data: The payload from the model with order details.

        Returns:
            A tuple of (is_valid, missing_fields). missing_fields contains keys that
            must be provided: ["menu_items", "delivery_date", "customer_name",
            "customer_phone", "customer_address"].
        """
        required_fields = [
            "menu_items",
            "delivery_date",
            "customer_name",
            "customer_phone",
            "customer_address",
        ]
        if not isinstance(data, dict):
            return False, required_fields

        missing: list[str] = []
        for key in required_fields:
            value = data.get(key)
            if value is None:
                missing.append(key)
                continue
            if isinstance(value, str) and not value.strip():
                missing.append(key)

        # Very light phone sanity check
        phone = data.get("customer_phone")
        if isinstance(phone, str):
            digits = "".join(ch for ch in phone if ch.isdigit())
            if len(digits) < 9:
                if "customer_phone" not in missing:
                    missing.append("customer_phone")

        return (len(missing) == 0), missing

    def _compose_missing_order_details_prompt(
        self, *, language: str, missing_fields: list[str]
    ) -> str:
        """Compose a localized prompt asking only for missing order details.

        Args:
            language: Target language code, e.g., "uk".
            missing_fields: List of missing field names.

        Returns:
            A short, polite message asking the customer for the missing details.
        """
        # Map technical keys to user-friendly labels
        labels_uk = {
            "menu_items": "позиції замовлення",
            "delivery_date": "дату доставки",
            "customer_name": "ім'я",
            "customer_phone": "номер телефону",
            "customer_address": "адресу доставки",
        }
        labels_en = {
            "menu_items": "order items",
            "delivery_date": "delivery date",
            "customer_name": "name",
            "customer_phone": "phone number",
            "customer_address": "delivery address",
        }

        labels = labels_uk if language == "uk" else labels_en
        parts = [labels.get(key, key) for key in missing_fields]

        if language == "uk":
            if len(parts) == 1:
                return f"Будь ласка, надайте {parts[0]}."
            if len(parts) == 2:
                return f"Будь ласка, надайте {parts[0]} та {parts[1]}."
            return (
                "Будь ласка, надайте відсутні дані: "
                + ", ".join(parts[:-1])
                + f" та {parts[-1]}."
            )
        else:
            if len(parts) == 1:
                return f"Please provide the {parts[0]}."
            if len(parts) == 2:
                return f"Please provide the {parts[0]} and {parts[1]}."
            return (
                "Please provide the missing details: "
                + ", ".join(parts[:-1])
                + f" and {parts[-1]}."
            )

    def get_conversation_history(self, conversation_id: int, db_session) -> list:
        try:
            from app.models.message import Message, MessageSender

            messages = (
                db_session.query(Message)
                .filter(Message.chat_id == conversation_id)
                .order_by(Message.timestamp.desc())
                .limit(20)
                .all()
            )

            history = []
            for msg in reversed(messages):
                role = "user" if msg.sender == MessageSender.USER else "assistant"
                history.append({"role": role, "content": msg.text})

            return history
        except Exception as e:
            logger.warning(f"Failed to retrieve conversation history: {e}")
            return []


async def main() -> None:
    start = time.time()
    assortment_agent = Agent(
        "assortment_agent",
        description="Specialized menu agent. Identifies event format (buffet/coffee-break/cocktail; banquet→escalate), collects guest_count + event_duration.",
        system_message=assortment_system_message,
        enable_memory=True,
        tools=[get_products_tool],
        model="gpt-4.1-mini"
    )
    print(time.time() - start)
    messages = [
        HumanMessage(
            content="Дитяче свято, 10 осіб, тривалість 3 години",
            additional_kwargs={},
            response_metadata={},
        )
    ]

    resp = await assortment_agent.execute(messages)
    print(resp)
    print(time.time() - start)
    # gp = get_products_tool.coroutine
    # result = await gp("ланчі")
    # print(result)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
