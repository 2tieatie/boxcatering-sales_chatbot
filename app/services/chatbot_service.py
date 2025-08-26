import json
from typing import Optional, Dict, Any
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
    ) -> ChatResponse:
        """Process a chat message and return response."""
        try:
            # Build the system prompt with language settings
            system_prompt = self._build_system_prompt(language, force_language, config)
            
            # Create the chat completion
            chosen_model = model or self.model
            request_kwargs = {
                "model": chosen_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chat_request.message},
                ],
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
                    "Перепрошую, я не зовсім зрозумів. Будь ласка, перефразуйте, я залюбки допоможу."
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

            return ChatResponse(
                response=user_text,
                handover_to_manager=needs_handover,
                handover_reason=handover_reason,
                handover_reason_description=handover_desc,
                debug=(
                    {
                        "model": request_kwargs.get("model"),
                        "temperature": request_kwargs.get("temperature"),
                        "max_tokens": request_kwargs.get("max_tokens") or request_kwargs.get("max_completion_tokens"),
                        "handover": needs_handover,
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

        language_instruction = ""
        if language == "uk":
            language_instruction = """
        ВАЖЛИВО: Ви ОБОВ'ЯЗКОВО повинні відповідати ТІЛЬКИ українською мовою. 
        Ніколи не використовуйте інші мови, навіть якщо клієнт пише англійською або іншою мовою.
        Всі ваші відповіді мають бути українською мовою.
        """
        elif force_language:
            language_instruction = f"""
        IMPORTANT: You MUST respond ONLY in {language} language.
        Never use other languages, even if the customer writes in a different language.
        All your responses must be in {language}.
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

        style_lines = []
        if friendly_tone:
            style_lines.append("Use a friendly and welcoming tone.")
        if professional_style:
            style_lines.append("Maintain professional, concise communication.")
        if suggestive_responses:
            style_lines.append(
                "When appropriate, suggest 1-3 short next steps or options to the customer."
            )

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
            """
        else:
            handover_block = """
        Do not request a handover to a human manager. Provide your best, most helpful answer directly to the customer.
            """

        return f"""
        You are a helpful AI assistant for a box catering business.
        {language_instruction}

        {('\n'.join(context_lines)) if context_lines else ''}

        Your role is to:
        1. Answer customer questions about services, menus, and pricing
        2. Help customers place orders
        3. Provide information about discounts and special offers
        4. Handle basic customer service inquiries

        {' '.join(style_lines)}

        {handover_block}

        Otherwise, respond normally with just your message to the customer.
        """
    
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
        # Per current assumption: 'gpt-5' doesn't support temperature; 'gpt-5-chat' and others do
        unsupported = {"gpt-5"}
        return model_name not in unsupported

    def _model_requires_max_completion_tokens(self, model_name: str) -> bool:
        """Return True if the model expects 'max_completion_tokens' instead of 'max_tokens'."""
        # Based on error message and current assumptions for GPT-5 family
        return model_name.startswith("gpt-5")
