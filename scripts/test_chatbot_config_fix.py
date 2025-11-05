#!/usr/bin/env python3
"""Test script to verify chatbot config API endpoint works correctly."""

import requests
import json
from typing import Dict, Any


def test_chatbot_config_creation(base_url: str = "http://localhost:8000") -> None:
    """Test chatbot configuration creation endpoint."""

    # Test data that matches the ChatbotConfigCreate schema
    test_config = {
        "name": "Test Boxcatering Configuration",
        "prompt": "Hello! I'm your AI-powered boxcatering assistant. How can I help you today?",
        "business_context": "We are a premium boxcatering service specializing in corporate events and private parties.",
        "language": "uk",
        "force_language": True,
        "is_active": False,
        "company_name": "Test Boxcatering Pro",
        "specializations": "Corporate events, Private parties, Dietary restrictions",
        "friendly_tone": True,
        "professional_style": True,
        "suggestive_responses": True,
        "manager_handover": True,
        "fallback_message": "I apologize, but I didn't quite understand that. Could you please rephrase?",
        "handover_message": "Let me connect you with one of our specialists.",
        "response_timeout": 30,
        "conversation_logging": True,
        "performance_analytics": True,
        "error_reporting": True,
    }

    print("Testing chatbot configuration creation...")
    print(f"Test data: {json.dumps(test_config, indent=2)}")

    try:
        # First, try to get the active config to see if any exists
        response = requests.get(f"{base_url}/chatbot-config/active")
        print(f"GET /chatbot-config/active status: {response.status_code}")

        if response.status_code == 200:
            existing_config = response.json()
            print(f"Existing active config: {existing_config['name']}")
        else:
            print("No existing active config found")

        # Test the creation endpoint
        response = requests.post(
            f"{base_url}/chatbot-config/",
            json=test_config,
            headers={"Content-Type": "application/json"},
        )

        print(f"POST /chatbot-config/ status: {response.status_code}")

        if response.status_code == 200:
            created_config = response.json()
            print("✅ Configuration created successfully!")
            print(f"Created config ID: {created_config['id']}")
            print(f"Created config name: {created_config['name']}")
            print(f"Is active: {created_config['is_active']}")
            print(f"Created at: {created_config['created_at']}")

            # Test getting the created config
            config_id = created_config["id"]
            get_response = requests.get(f"{base_url}/chatbot-config/{config_id}")
            print(f"GET /chatbot-config/{config_id} status: {get_response.status_code}")

            if get_response.status_code == 200:
                retrieved_config = get_response.json()
                print("✅ Configuration retrieved successfully!")
                print(f"Retrieved config: {retrieved_config['name']}")
            else:
                print(f"❌ Failed to retrieve config: {get_response.text}")

        else:
            print(f"❌ Failed to create configuration: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print(
            "❌ Connection error: Make sure the server is running on http://localhost:8000"
        )
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def test_schema_validation(base_url: str = "http://localhost:8000") -> None:
    """Test schema validation with invalid data."""

    print("\nTesting schema validation...")

    # Test with missing required fields
    invalid_config = {
        "name": "",  # Empty name should fail
        "prompt": "Valid prompt",
        # Missing business_context should fail
        "language": "uk",
    }

    try:
        response = requests.post(
            f"{base_url}/chatbot-config/",
            json=invalid_config,
            headers={"Content-Type": "application/json"},
        )

        print(f"POST with invalid data status: {response.status_code}")

        if response.status_code == 422:
            print("✅ Schema validation working correctly - rejected invalid data")
            error_details = response.json()
            print(f"Validation errors: {json.dumps(error_details, indent=2)}")
        else:
            print(f"❌ Expected validation error, got: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print(
            "❌ Connection error: Make sure the server is running on http://localhost:8000"
        )
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    print("🧪 Testing Chatbot Configuration API Endpoints")
    print("=" * 50)

    test_chatbot_config_creation()
    test_schema_validation()

    print("\n" + "=" * 50)
    print("Testing completed!")
