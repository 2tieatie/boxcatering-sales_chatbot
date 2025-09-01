"""Chatbot service for AI interactions."""

import json
import os
from typing import Optional
from openai import OpenAI
from loguru import logger

from app.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, HandoverReason


class ChatbotService:
    """Service for handling chatbot interactions."""
    
    def __init__(self):
        # Get API key from environment or use a placeholder
        api_key = os.getenv("OPENAI_API_KEY") or "placeholder_key"
        model = os.getenv("OPENAI_MODEL") or "gpt-4o"
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    async def process_message(self, chat_request: ChatRequest, language: str = "uk", force_language: bool = True) -> ChatResponse:
        """Process a chat message and return response."""
        try:
            # Build the system prompt with language settings
            system_prompt = self._build_system_prompt(language, force_language)
            
            # Create the chat completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chat_request.message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
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
