#!/usr/bin/env python3
"""
Debug script to test chatbot config API and see exact validation errors.
"""

import requests
import json
from loguru import logger

BASE_URL = "http://localhost:8000"


def debug_chatbot_config():
    """Debug the chatbot config API validation."""
    logger.info("🔍 Debugging chatbot config API validation...")

    # Test data that should match the schema
    test_config = {
        "name": "Test Debug Config",
        "prompt": "Hello! I am a test chatbot.",
        "business_context": "This is a test business context.",
        "language": "en",
        "force_language": True,
        "is_active": True,
        "company_name": "Test Company",
        "specializations": "Test specializations",
        "friendly_tone": True,
        "professional_style": True,
        "suggestive_responses": True,
        "manager_handover": True,
        "fallback_message": "I did not understand that.",
        "handover_message": "Let me connect you to a manager.",
        "response_timeout": 30,
        "conversation_logging": True,
        "performance_analytics": True,
        "error_reporting": True,
    }

    try:
        # Test with invalid token to see the validation error
        logger.info("🧪 Testing with invalid token to see validation error...")
        response = requests.post(
            f"{BASE_URL}/chatbot-config/",
            json=test_config,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid_token",
            },
        )

        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {response.text}")

        if response.status_code == 422:
            try:
                error_data = response.json()
                logger.error("🔴 Validation Error Details:")
                if "detail" in error_data:
                    for error in error_data["detail"]:
                        logger.error(f"  - Field: {error.get('loc', 'unknown')}")
                        logger.error(f"    Type: {error.get('type', 'unknown')}")
                        logger.error(f"    Message: {error.get('msg', 'unknown')}")
                        logger.error(f"    Input: {error.get('input', 'unknown')}")
            except:
                logger.error(f"Raw error response: {response.text}")

        # Test without any data to see what's required
        logger.info("\n🧪 Testing with empty data...")
        response = requests.post(
            f"{BASE_URL}/chatbot-config/",
            json={},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid_token",
            },
        )

        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        logger.error("❌ Could not connect to the API server")
        logger.info("💡 Make sure the server is running on http://localhost:8000")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    debug_chatbot_config()
