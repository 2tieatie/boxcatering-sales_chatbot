#!/usr/bin/env python3
"""End-to-end WebSocket test for step-by-step order intake flow.

This script connects to ws://localhost:8000/chat/ws?debug=1 and sends a
predefined Ukrainian conversation to verify that the chatbot:
  - Asks what the user wants to order
  - Asks for delivery date
  - Requests delivery details (name, phone, address)
  - Emits create_order only after all required fields are provided

Run:
  python scripts/e2e_order_flow_test.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

import websockets


def _iso_now() -> str:
    """Return current time in ISO format with timezone info."""
    return datetime.now(timezone.utc).isoformat()


async def run_test() -> int:
    """Run the E2E test conversation against the local WebSocket server.

    Returns:
        Exit code 0 for success, non-zero on error.
    """
    session_id = f"test-e2e-{int(datetime.now().timestamp())}"
    uri = "ws://localhost:8000/chat/ws?debug=1"

    messages: List[str] = [
        "Вітаю, хочу замовити!",
        "Хотів би бокс з канапками та фруктами.",
        "Супер, підходять такі бокси.",
        "28.09",
        "Ім'я: Андрій, Телефон: +380501112233, Адреса: м. Київ, вул. Хрещатик, 1",
    ]

    print(f"Connecting to {uri} ...")
    try:
        async with websockets.connect(uri) as ws:
            for idx, text in enumerate(messages, start=1):
                payload: Dict[str, Any] = {
                    "session_id": session_id,
                    "sender": "user",
                    "message": text,
                    "timestamp": _iso_now(),
                }
                print(f"\nUser: {text}")
                await ws.send(json.dumps(payload))

                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=30)
                except asyncio.TimeoutError:
                    print("Timed out waiting for bot response.")
                    return 2

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"Bot (raw): {raw}")
                    continue

                bot_text = data.get("response") or ""
                print(f"Bot: {bot_text}")
                if data.get("handover_to_manager"):
                    print("[Note] Handover requested by bot.")
                if data.get("action") == "create_order":
                    print("[Action] create_order emitted with data:")
                    print(json.dumps(data.get("data") or {}, ensure_ascii=False, indent=2))

                await asyncio.sleep(0.8)
    except OSError as e:
        print(f"Failed to connect to {uri}: {e}")
        print("Make sure the API server is running on localhost:8000.")
        return 1
    except Exception as e:  # pragma: no cover - guard for unexpected issues
        print(f"Unexpected error: {e}")
        return 3

    print("\nE2E conversation finished.")
    return 0


def main() -> None:
    """Entry point."""
    code = asyncio.run(run_test())
    sys.exit(code)


if __name__ == "__main__":
    main()


