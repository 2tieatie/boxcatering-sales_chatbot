"""Workflow tests for chatbot configuration versions and chat behavior."""

import types
from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base
from app.models.chatbot_config import ChatbotConfig
from app.dependencies import (
    get_db as real_get_db,
    require_admin_or_system_admin_dependency,
    get_current_active_user_dependency,
)
from app.schemas.chat import ChatResponse


@pytest.fixture()
def test_client() -> Generator[TestClient, None, None]:
    """Provide a TestClient with an in-memory test database and auth overrides."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def get_db_override() -> Generator:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Simple user surrogate
    fake_user = types.SimpleNamespace(
        id=1, username="admin", role="admin", is_active=True
    )

    # Dependency overrides
    app.dependency_overrides[real_get_db] = get_db_override
    app.dependency_overrides[require_admin_or_system_admin_dependency] = (
        lambda: fake_user
    )
    app.dependency_overrides[get_current_active_user_dependency] = lambda: fake_user

    client = TestClient(app)

    # Seed initial data
    with TestingSessionLocal() as db:
        active = ChatbotConfig(
            name="Default Active",
            welcome_message="Hello from active",
            business_context="Box Catering",
            language="uk",
            force_language=True,
            is_active=True,
            chatbot_name="Marichka",
        )
        other = ChatbotConfig(
            name="Draft 22",
            welcome_message="Hello from draft",
            business_context="Box Catering",
            language="uk",
            force_language=True,
            is_active=False,
            chatbot_name="Porichka",
        )
        db.add(active)
        db.add(other)
        db.commit()

    try:
        yield client
    finally:
        # Clean up overrides
        app.dependency_overrides.pop(real_get_db, None)
        app.dependency_overrides.pop(require_admin_or_system_admin_dependency, None)
        app.dependency_overrides.pop(get_current_active_user_dependency, None)


def _get_configs(client: TestClient):
    resp = client.get("/chatbot-config/?limit=50")
    assert resp.status_code == 200
    data = resp.json()
    # Map by chatbot_name for convenience
    by_name = {c["chatbot_name"]: c for c in data}
    return data, by_name


def test_put_update_non_active_does_not_change_active(test_client: TestClient):
    # Verify active is Marichka
    resp = test_client.get("/chatbot-config/active")
    assert resp.status_code == 200
    assert resp.json()["chatbot_name"] == "Marichka"

    # Find draft (Porichka) id
    _, by_name = _get_configs(test_client)
    draft = by_name["Porichka"]
    draft_id = draft["id"]

    # Update only the draft config via PUT (simulate editing a non-active config)
    upd = {"chatbot_name": "Porichka"}
    resp2 = test_client.put(f"/chatbot-config/{draft_id}", json=upd)
    assert resp2.status_code == 200
    assert resp2.json()["id"] == draft_id
    assert resp2.json()["chatbot_name"] == "Porichka"

    # Active config must remain unchanged
    resp3 = test_client.get("/chatbot-config/active")
    assert resp3.status_code == 200
    assert resp3.json()["chatbot_name"] == "Marichka"


def test_chat_websocket_uses_active_config_by_default(
    test_client: TestClient, monkeypatch
):
    # Identify active id
    resp = test_client.get("/chatbot-config/active")
    active_id = resp.json()["id"]

    # Monkeypatch ChatbotService.process_message to echo selected config id
    from app.api import chat as chat_api

    async def fake_process_message(
        *,
        chat_request,
        language,
        force_language,
        model,
        temperature,
        max_tokens,
        debug,
        config,
        conversation_history,
    ):
        selected = (config or {}).get("id")
        return ChatResponse(response=str(selected or "none"), handover_to_manager=False)

    chat_api.chatbot_service.process_message = fake_process_message  # type: ignore

    # Open WebSocket and send a message
    with test_client.websocket_connect("/chat/ws") as ws:
        payload = {
            "session_id": "sess-1",
            "sender": "user",
            "message": "hi",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        ws.send_json(payload)
        data = ws.receive_json()
        # The response should be the active config id (as string)
        assert data["response"] == str(active_id)
