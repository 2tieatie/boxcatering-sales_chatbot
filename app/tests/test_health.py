"""Test health endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.chatbot_service import ChatbotService
from app.schemas.chat import ChatRequest

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "uptime" in data


def test_prompt_mentions_kyiv_odesa_delivery_policy():
    """System prompt should contain explicit Kyiv/Odesa delivery coverage cue."""
    service = ChatbotService()
    # Build prompt in Ukrainian (default language in app)
    prompt = service._build_system_prompt(
        language="uk", force_language=True, config=None
    )
    assert "доставляємо лише в Києві та Одесі" in prompt
