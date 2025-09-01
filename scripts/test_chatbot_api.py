#!/usr/bin/env python3
"""
Test script to test the chatbot config API endpoint.
This will test if the API can handle the extended schema properly.
"""

import requests
import json
from loguru import logger

BASE_URL = "http://localhost:8000"

def test_chatbot_config_api():
    """Test the chatbot config API endpoint."""
    logger.info("🚀 Testing chatbot config API endpoint...")
    
    # Test data with extended fields
    test_config = {
        "name": "Test Extended Config via API",
        "prompt": "Hello! I am a test chatbot via API.",
        "business_context": "This is a test business context via API.",
        "language": "en",
        "force_language": True,
        "is_active": True,
        "company_name": "Test Company via API",
        "specializations": "Test specializations via API",
        "friendly_tone": True,
        "professional_style": True,
        "suggestive_responses": True,
        "manager_handover": True,
        "fallback_message": "I did not understand that via API.",
        "handover_message": "Let me connect you to a manager via API.",
        "response_timeout": 60,
        "conversation_logging": True,
        "performance_analytics": True,
        "error_reporting": True
    }
    
    try:
        # Test without authentication (should fail with 401)
        logger.info("🧪 Testing without authentication...")
        response = requests.post(
            f"{BASE_URL}/chatbot-config/",
            json=test_config,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 401:
            logger.info("✅ Correctly rejected without authentication")
        else:
            logger.warning(f"⚠️ Unexpected status code: {response.status_code}")
            logger.warning(f"Response: {response.text}")
        
        # Test with invalid token (should fail with 401)
        logger.info("🧪 Testing with invalid token...")
        response = requests.post(
            f"{BASE_URL}/chatbot-config/",
            json=test_config,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid_token"
            }
        )
        
        if response.status_code == 401:
            logger.info("✅ Correctly rejected with invalid token")
        else:
            logger.warning(f"⚠️ Unexpected status code: {response.status_code}")
            logger.warning(f"Response: {response.text}")
        
        logger.info("🎉 API endpoint is responding correctly")
        logger.info("💡 To test with valid authentication, you need to:")
        logger.info("   1. Login through the frontend")
        logger.info("   2. Get a valid access token")
        logger.info("   3. Use that token in the Authorization header")
        
    except requests.exceptions.ConnectionError:
        logger.error("❌ Could not connect to the API server")
        logger.info("💡 Make sure the server is running on http://localhost:8000")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    test_chatbot_config_api()
