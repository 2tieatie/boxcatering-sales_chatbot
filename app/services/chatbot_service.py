import json
# import os
# from typing import Optional
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
    ) -> ChatResponse:
        """Process a chat message and return response."""
        try:
            # Build the system prompt with language settings
            system_prompt = self._build_system_prompt(language, force_language)
            
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
                else:
                    raise
            
            # Extract the response
            ai_response = response.choices[0].message.content
            
            # Parse the response to check for handover
            parsed_response = self._parse_ai_response(ai_response)
            
            return ChatResponse(
                response=parsed_response.get("response", ai_response),
                handover_to_manager=parsed_response.get("handover_to_manager", False),
                handover_reason=parsed_response.get("handover_reason"),
                handover_reason_description=parsed_response.get("handover_reason_description")
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Return a fallback response
            return ChatResponse(
                response="I apologize, but I'm experiencing technical difficulties. Please try again later.",
                handover_to_manager=True,
                handover_reason=HandoverReason.TECH_OR_FINANCIAL_LIMITATION,
                handover_reason_description="Technical error in AI service"
            )
    
    def _build_system_prompt(self, language: str = "uk", force_language: bool = True) -> str:
        """Build the system prompt for the AI."""
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
        
        return f"""
        You are a helpful AI assistant for a box catering business. Your role is to:
        1. Answer customer questions about our services, menus, and pricing
        2. Help customers place orders
        3. Provide information about discounts and special offers
        4. Handle basic customer service inquiries
        
        {language_instruction}
        
        If you encounter any of the following situations, you should request a handover to a human manager:
        - You're not confident in your answer (LOW_CONFIDENCE)
        - The request is outside your scope (OUT_OF_SCOPE)
        - Sensitive cases like complaints or VIP customers (SENSITIVE_CASE)
        - Technical or financial limitations (TECH_OR_FINANCIAL_LIMITATION)
        - Customer directly requests to speak with a manager (USER_REQUEST_MANAGER)
        
        When requesting handover, respond in this JSON format:
        {{
            "response": "Your response to the customer",
            "handover_to_manager": true,
            "handover_reason": "REASON_CODE",
            "handover_reason_description": "Brief description of why handover is needed"
        }}
        
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
