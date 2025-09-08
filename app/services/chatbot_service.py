import json
from pathlib import Path
from typing import Optional, Dict, Any
import io
import csv
from openai import OpenAI
from loguru import logger

from app.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, HandoverReason


class ChatbotService:
    """Service for handling chatbot interactions."""
    
    def __init__(self):
        # Get API key from environment or use a placeholder
        api_key = settings.openai_api_key
        model = settings.openai_model
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        # Cache combined context by cache key (absolute_dir|max_chars)
        self._context_docs_cache: Dict[str, str] = {}
    
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
        """Process a chat message and return response."""
        try:
            # Build the system prompt with language settings and context docs
            system_prompt = self._build_system_prompt(language, force_language, config)
            
            # Build conversation messages with history
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-10:]:  # Keep last 10 messages for context
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
            
            # Add current user message
            messages.append({"role": "user", "content": chat_request.message})
            
            # Create the chat completion
            chosen_model = model or self.model
            request_kwargs = {
                "model": chosen_model,
                "messages": messages,
            }

            # Respect model capabilities: only send temperature if supported
            if self._model_supports_temperature(chosen_model):
                request_kwargs["temperature"] = (
                    temperature if temperature is not None else getattr(settings, "openai_temperature", 0.7)
                )

            # Use correct parameter name for token limit based on model
            token_limit = max_tokens if max_tokens is not None else getattr(settings, "openai_max_tokens", 500)
            if self._model_requires_max_completion_tokens(chosen_model):
                request_kwargs["max_completion_tokens"] = token_limit
            else:
                request_kwargs["max_tokens"] = token_limit

            try:
                response = self.client.chat.completions.create(**request_kwargs)
            except Exception as api_error:
                error_text = str(api_error)
                default_model = self.model
                # If selected model is unavailable, retry once with default model
                if (
                    ("model_not_found" in error_text or "does not exist" in error_text)
                    and chosen_model != default_model
                ):
                    logger.warning(
                        f"Model '{chosen_model}' unavailable. Falling back to default model '{default_model}'."
                    )
                    fallback_kwargs = {
                        "model": default_model,
                        "messages": request_kwargs["messages"],
                    }
                    # Only include temperature if supported by fallback model
                    if self._model_supports_temperature(default_model):
                        fallback_kwargs["temperature"] = request_kwargs.get("temperature")
                    # Token limit parameter per fallback model
                    token_limit = (
                        request_kwargs.get("max_tokens")
                        or request_kwargs.get("max_completion_tokens")
                        or getattr(settings, "openai_max_tokens", 500)
                    )
                    if self._model_requires_max_completion_tokens(default_model):
                        fallback_kwargs["max_completion_tokens"] = token_limit
                    else:
                        fallback_kwargs["max_tokens"] = token_limit

                    response = self.client.chat.completions.create(**fallback_kwargs)
                    if debug:
                        request_kwargs = fallback_kwargs
                else:
                    raise
            
            # Extract the response
            ai_response = (response.choices[0].message.content or "")
            logger.debug(f"AI response: {ai_response}")
            logger.debug(f"Response: {response}")

            # Parse the response to check for handover
            parsed_response = self._parse_ai_response(ai_response)
            logger.debug(f"Parsed response: {parsed_response}")

            # Backend safety net: never return empty customer-visible text
            user_text = (parsed_response.get("response") or ai_response or "").strip()
            logger.debug(f"User text: {user_text}")
            needs_handover = bool(parsed_response.get("handover_to_manager", False))
            logger.debug(f"Needs handover: {needs_handover}")
            handover_reason = parsed_response.get("handover_reason")
            logger.debug(f"Handover reason: {handover_reason}")
            handover_desc = parsed_response.get("handover_reason_description")
            logger.debug(f"Handover description: {handover_desc}")

            # Messages from configuration or localized defaults
            default_fallback = (
                (config or {}).get("fallback_message")
                or (
                    "Перепрошую, я не зовсім зрозуміла. Будь ласка, перефразуйте, я залюбки допоможу."
                    if language == "uk"
                    else "I apologize, I didn't quite understand. Could you please rephrase? I'm happy to help."
                )
            )
            default_handover_msg = (
                (config or {}).get("handover_message")
                or (
                    "Вибачте, я не маю потрібної інформації. Передаю запит менеджеру."
                    if language == "uk"
                    else "I'm sorry, I don't have the required information. Let me forward your request to the manager."
                )
            )

            if not user_text:
                # If model responded with empty text, force a graceful handover
                allow_handover = bool((config or {}).get("manager_handover", True))
                if allow_handover:
                    return ChatResponse(
                        response=default_handover_msg,
                        handover_to_manager=True,
                        handover_reason=HandoverReason.OUT_OF_SCOPE,
                        handover_reason_description=(handover_desc or "Model returned empty response"),
                        debug=(
                            {
                                "model": request_kwargs.get("model"),
                                "temperature": request_kwargs.get("temperature"),
                                "max_tokens": request_kwargs.get("max_tokens") or request_kwargs.get("max_completion_tokens"),
                                "reason": "empty_text_fallback",
                            }
                            if debug
                            else None
                        ),
                    )
                # If handover disabled, use fallback message without handover
                return ChatResponse(
                    response=default_fallback,
                    handover_to_manager=False,
                    handover_reason=None,
                    handover_reason_description=(handover_desc or "Model returned empty response"),
                    debug=(
                        {
                            "model": request_kwargs.get("model"),
                            "temperature": request_kwargs.get("temperature"),
                            "max_tokens": request_kwargs.get("max_tokens") or request_kwargs.get("max_completion_tokens"),
                            "reason": "empty_text_no_handover",
                        }
                        if debug
                        else None
                    ),
                )

            # If handover requested but without a message, include an apology
            if needs_handover and not (parsed_response.get("response") or "").strip():
                user_text = default_handover_msg
                if not handover_reason:
                    handover_reason = HandoverReason.OUT_OF_SCOPE
                if not handover_desc:
                    handover_desc = "Handover requested without a user message"

            # Respect manager_handover flag
            if needs_handover and not bool((config or {}).get("manager_handover", True)):
                needs_handover = False
                if not user_text:
                    user_text = default_fallback

            # Prepare optional action/data if model requested structured action (e.g., create order)
            action = None
            data = None
            try:
                if isinstance(parsed_response, dict):
                    action = parsed_response.get("action")
                    payload = parsed_response.get("data")
                    if action and isinstance(payload, dict):
                        data = payload
                    # Backward-compat alias: allow { create_order: {...} }
                    if not action and "create_order" in parsed_response:
                        action = "create_order"
                        maybe_payload = parsed_response.get("create_order")
                        if isinstance(maybe_payload, dict):
                            data = maybe_payload
            except Exception:
                action = None
                data = None

            return ChatResponse(
                response=user_text,
                handover_to_manager=needs_handover,
                handover_reason=handover_reason,
                handover_reason_description=handover_desc,
                action=action,
                data=data,
                debug=(
                    {
                        "model": request_kwargs.get("model"),
                        "temperature": request_kwargs.get("temperature"),
                        "max_tokens": request_kwargs.get("max_tokens") or request_kwargs.get("max_completion_tokens"),
                        "handover": needs_handover,
                        **({"action": action} if action else {}),
                    }
                    if debug
                    else None
                ),
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Return a fallback response
            return ChatResponse(
                response=("Перепрошую, але в мене виникли технічні проблеми. Будь ласка, спробуйте пізніше." 
                          if language == "uk" 
                          else "I apologize, but I'm experiencing technical difficulties. Please try again later."),
                handover_to_manager=True,
                handover_reason=HandoverReason.TECH_OR_FINANCIAL_LIMITATION,
                handover_reason_description="Technical error in AI service"
            )
    
    def _build_system_prompt(
        self,
        language: str = "uk",
        force_language: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the system prompt for the AI using chatbot settings."""

        # More natural language instruction
        language_instruction = ""
        if language == "uk":
            language_instruction = """
        Мова спілкування: Завжди відповідайте українською мовою, навіть якщо клієнт пише іншою мовою. 
        Це допоможе створити комфортну атмосферу для наших клієнтів.
        """
        elif force_language:
            language_instruction = f"""
        Language: Always respond in {language}, even if the customer writes in another language. 
        This helps create a comfortable atmosphere for our customers.
        """

        # Enhanced persona with more personality
        persona_instruction = ""
        if language == "uk":
            persona_instruction = """
        Ваша особистість: Ви — Марічка, дружня та професійна асистентка з кейтерингу. 
        Ви ентузіастка свого діла, завжди готова допомогти клієнтам знайти ідеальне рішення для їх заходів.
        Спілкуйтеся тепло та природно, як справжня людина. Використовуйте емоції, емодзі (але не надто багато), 
        та робіть розмову живою та цікавою. Пам'ятайте деталі з попередніх повідомлень та не повторюйте питання.
        Пишіть завжди від першої особи в жіночому роді. Уникайте звертання в чоловічому роді.
        """
        else:
            persona_instruction = """
        Your personality: You are Marichka, a friendly and professional catering assistant. 
        You're passionate about your work and always ready to help customers find the perfect solution for their events.
        Communicate warmly and naturally, like a real person. Use emotions, emojis (but not too many), 
        and make conversations lively and engaging. Remember details from previous messages and don't repeat questions.
        Write in first person using feminine wording when applicable. Avoid masculine phrasing.
        """

        company_name = (config or {}).get("company_name")
        business_context = (config or {}).get("business_context")
        specializations = (config or {}).get("specializations")
        friendly_tone = bool((config or {}).get("friendly_tone", True))
        professional_style = bool((config or {}).get("professional_style", True))
        suggestive_responses = bool((config or {}).get("suggestive_responses", True))
        manager_handover = bool((config or {}).get("manager_handover", True))

        context_lines = []
        if company_name:
            context_lines.append(f"Company: {company_name}")
        if business_context:
            context_lines.append(f"Business Context: {business_context}")
        if specializations:
            context_lines.append(f"Specializations: {specializations}")

        # Enhanced conversational style instructions
        style_lines = []
        if language == "uk":
            if friendly_tone:
                style_lines.append("Спілкуйтеся тепло та дружньо, як з близькою людиною.")
            if professional_style:
                style_lines.append("Залишайтеся професійною, але не формальною. Будьте природною та живою.")
            if suggestive_responses:
                style_lines.append(
                    "Коли це доречно, пропонуйте 1-3 короткі наступні кроки або варіанти клієнту. "
                    "Завжди пояснюйте, чому саме ці варіанти підходять."
                )
            style_lines.extend([
                "Використовуйте природні переходи між темами та питаннями.",
                "Показуйте справжній інтерес до потреб клієнта.",
                "Якщо клієнт згадував щось раніше, посилайтеся на це в розмові.",
                "Задавайте уточнюючі питання, але не надто багато одночасно.",
                "Використовуйте емодзі помірно (1-2 на повідомлення), щоб зробити розмову живішою."
            ])
        else:
            if friendly_tone:
                style_lines.append("Communicate warmly and friendly, like with a close person.")
            if professional_style:
                style_lines.append("Stay professional but not formal. Be natural and lively.")
            if suggestive_responses:
                style_lines.append(
                    "When appropriate, suggest 1-3 short next steps or options to the customer. "
                    "Always explain why these options are suitable."
                )
            style_lines.extend([
                "Use natural transitions between topics and questions.",
                "Show genuine interest in the customer's needs.",
                "If the customer mentioned something earlier, refer to it in the conversation.",
                "Ask clarifying questions, but not too many at once.",
                "Use emojis moderately (1-2 per message) to make conversations livelier."
            ])

        handover_block = ""
        
        if manager_handover:
            handover_block = """
        If you encounter any of the following situations, you should request a handover to a human manager.
        Assign a reason code to the handover:
        
        - "LOW_CONFIDENCE" - You're not confident in your answer
        - "OUT_OF_SCOPE" - The request is outside your scope (you don't have the information)
        - "SENSITIVE_CASE" - Sensitive cases like complaints or VIP customers
        - "TECH_OR_FINANCIAL_LIMITATION" - Technical or financial limitations
        - "USER_REQUEST_MANAGER" - Customer directly requests to speak with a manager
        
        When requesting handover, respond in this JSON format:
        
        {
            "response": "Your response to the customer",
            "handover_to_manager": true,
            "handover_reason": "<REASON_CODE>",
            "handover_reason_description": "Brief description of why handover is needed"
        }

        Important:
        - Only the value of "response" will be shown to the customer.
        - The other JSON fields are used internally to notify a manager (e.g., via Telegram) and will not be visible to the customer.
        - Craft "response" as a short, polite message informing the customer that a manager will take over soon. Do not include the JSON itself or technical details in "response".
        - Keep any sensitive or operational details in the JSON fields, not in the "response" text.
            """
        else:
            handover_block = """
        Do not request a handover to a human manager. Provide your best, most helpful answer directly to the customer.
            """

        context_docs_block = self._get_context_block(config)

        return f"""
        You are a helpful AI assistant for a catering business.
        {language_instruction}
        {persona_instruction}

        {('\n'.join(context_lines)) if context_lines else ''}

        Your goal is to make customers' ordering experience as convenient and pleasant as possible:
        • Answer questions about menus, prices, and services
        • Help customers place orders step by step
        • Share information about discounts and special offers
        • Handle any customer service inquiries

        {'\n'.join(style_lines)}

        {handover_block}

        If the customer clearly wants to place an order, ask for the customer's
        name and phone number, customer address and menu items to include in the order,
        then emit a JSON object with `create_order` action, followed by a short human-friendly
        confirmation message. Use this format exactly:

        {{
            "response": "<your short confirmation to the user in {language}>",
            "action": "create_order",
            "data": {{
                "customer_name": "<name>",
                "customer_phone": "<phone>",
                "customer_email": "<optional email>",
                "customer_address": "<address>",
                "menu_items": "<menu items>",
                "total_amount": <number>,
                "delivery_date": "<date in ISO format YYYY-MM-DD>",
                "delivery_time": "<time>",
                "notes": "<optional notes>",
                "currency": "UAH",
            }}
        }}

        If some required details are missing (like name or phone number), ask a
        concise follow-up question instead of emitting the action. When all non-optional
        info is gathered, emit the `create_order` action as above.

        {context_docs_block}

        Otherwise, respond normally with just your message to the customer.
        """
    
    def _get_context_block(self, config: Optional[Dict[str, Any]] = None) -> str:
        """Return a formatted context block built from local documents.

        Reads and caches files from the directory configured by
        settings or per-request overrides in `config` when enabled.
        Content is trimmed to the provided max chars to keep prompts
        within reasonable limits.
        """
        try:
            enabled_override = None
            if config is not None:
                enabled_override = config.get("context_docs_enabled")
            enabled = (
                bool(enabled_override)
                if enabled_override is not None
                else bool(getattr(settings, "context_docs_enabled", True))
            )
            if not enabled:
                return ""

            dir_override = (config or {}).get("context_docs_dir") if config else None
            max_chars_override = (config or {}).get("context_docs_max_chars") if config else None

            docs_dir = Path(dir_override or getattr(settings, "context_docs_dir", "agent_context_documents"))
            if not docs_dir.is_absolute():
                docs_dir = Path.cwd() / docs_dir

            try:
                max_chars = int(max_chars_override) if max_chars_override is not None else int(getattr(settings, "context_docs_max_chars", 4000))
            except Exception:
                max_chars = int(getattr(settings, "context_docs_max_chars", 4000))

            cache_key = f"{str(docs_dir)}|{max_chars}"
            combined = self._context_docs_cache.get(cache_key)
            if combined is None:
                combined = self._load_context_documents(docs_dir, max_chars)
                # Cache even empty string so we don't keep hitting disk
                self._context_docs_cache[cache_key] = combined

            if not combined:
                return ""
            return (
                "Use the following Business Knowledge Base when answering. "
                "Prefer it over assumptions. If the information is not in the "
                "knowledge base, answer politely based on your general knowledge "
                "and indicate limitations when appropriate.\n\n"
                "[Business Knowledge Base]\n" + combined
            )
        except Exception as e:
            logger.warning(f"Failed to build context block: {e}")
            return ""

    def _load_context_documents(self, docs_dir: Path, max_chars: int) -> str:
        """Load context documents from disk and return a combined string.

        Returns an empty string on error or when no documents are found.
        Supports `.md`, `.txt`, `.pdf`, `.docx`, `.csv`. Files are concatenated
        in name-sorted order.
        """
        try:
            if not docs_dir.exists() or not docs_dir.is_dir():
                logger.info(f"Context docs directory not found: {docs_dir}")
                return ""

            parts: list[str] = []
            for path in sorted(docs_dir.rglob("*")):
                if not path.is_file():
                    continue
                ext = path.suffix.lower()
                if ext not in {".md", ".txt", ".pdf", ".docx", ".csv"}:
                    continue
                try:
                    text = ""
                    if ext in {".md", ".txt"}:
                        text = path.read_text(encoding="utf-8")
                    elif ext == ".pdf":
                        try:
                            # Prefer PyPDF2 if available
                            import PyPDF2  # type: ignore

                            with path.open("rb") as f:
                                reader = PyPDF2.PdfReader(f)
                                buf: list[str] = []
                                for page in reader.pages:
                                    try:
                                        buf.append(page.extract_text() or "")
                                    except Exception:
                                        pass
                                text = "\n".join([t.strip() for t in buf if t and t.strip()])
                        except Exception as pdf_err:
                            logger.warning(f"Failed to parse PDF {path}: {pdf_err}")
                            text = ""
                    elif ext == ".docx":
                        try:
                            # python-docx
                            from docx import Document  # type: ignore

                            doc = Document(str(path))
                            paras = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
                            text = "\n".join(paras)
                        except Exception as docx_err:
                            logger.warning(f"Failed to parse DOCX {path}: {docx_err}")
                            text = ""
                    elif ext == ".csv":
                        try:
                            with path.open("r", encoding="utf-8", newline="") as f:
                                reader = csv.reader(f)
                                rows: list[str] = []
                                for row in reader:
                                    try:
                                        rows.append(", ".join([col.strip() for col in row if col is not None]))
                                    except Exception:
                                        pass
                                text = "\n".join(rows)
                        except Exception as csv_err:
                            logger.warning(f"Failed to parse CSV {path}: {csv_err}")
                            text = ""

                    if text.strip():
                        # Add a lightweight header with the filename for model context
                        parts.append(f"## {path.stem}\n\n{text.strip()}\n")
                except Exception as read_err:
                    logger.warning(f"Failed to read context file {path}: {read_err}")

            combined = "\n\n".join(parts).strip()
            if not combined:
                return ""

            if max_chars and len(combined) > max_chars:
                combined = combined[:max_chars]
            return combined
        except Exception as e:
            logger.warning(f"Failed loading context documents: {e}")
            return ""

    def _parse_ai_response(self, response: str) -> dict:
        """Parse AI response to extract handover information."""
        try:
            # Try to parse as JSON
            if response.strip().startswith("{"):
                parsed = json.loads(response)
                return parsed
        except json.JSONDecodeError:
            pass
        
        # If not JSON, return as regular response
        return {"response": response, "handover_to_manager": False}

    def _model_supports_temperature(self, model_name: str) -> bool:
        """Return True if temperature is supported for the given model."""

        unsupported = {"gpt-5", "gpt-5-mini", "gpt-5-nano"}
        return model_name not in unsupported

    def _model_requires_max_completion_tokens(self, model_name: str) -> bool:
        """Return True if the model expects 'max_completion_tokens' instead of 'max_tokens'."""
        # Based on error message and current assumptions for GPT-5 family
        return model_name.startswith("gpt-5")
    
    def get_conversation_history(self, conversation_id: int, db_session) -> list:
        """Retrieve conversation history for context."""
        try:
            from app.models.message import Message, MessageSender
            
            # Get last 20 messages from the conversation
            messages = (
                db_session.query(Message)
                .filter(Message.chat_id == conversation_id)
                .order_by(Message.timestamp.desc())
                .limit(20)
                .all()
            )
            
            # Convert to OpenAI format and reverse to chronological order
            history = []
            for msg in reversed(messages):
                role = "user" if msg.sender == MessageSender.USER else "assistant"
                history.append({
                    "role": role,
                    "content": msg.text
                })
            
            return history
        except Exception as e:
            logger.warning(f"Failed to retrieve conversation history: {e}")
            return []
