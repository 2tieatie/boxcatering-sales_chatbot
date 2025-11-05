#!/usr/bin/env python3
"""
Test script for system configuration API endpoints.
This script tests the new system configuration functionality.
"""

import os
import sys
import requests
import json

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def get_auth_token():
    """Get authentication token for admin user."""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return None


def test_get_all_settings(token):
    """Test getting all settings."""
    print("🧪 Testing GET /system-config/settings/all...")

    try:
        response = requests.get(
            f"{BASE_URL}/system-config/settings/all",
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 200:
            settings = response.json()
            print("✅ Successfully retrieved all settings:")
            for category, configs in settings.items():
                print(f"  {category}: {len(configs)} configurations")
                for key, value in configs.items():
                    # Mask sensitive values
                    display_value = (
                        "***"
                        if key in ["api_key", "bot_token", "jwt_secret"]
                        else value
                    )
                    print(f"    {key}: {display_value}")
            return True
        else:
            print(
                f"❌ Failed to get settings: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"❌ Error getting settings: {e}")
        return False


def test_save_openai_settings(token):
    """Test saving OpenAI settings."""
    print("\n🧪 Testing POST /system-config/settings/openai...")

    try:
        settings = {
            "api_key": "test_openai_key_123",
            "model": "gpt-4o",
            "max_tokens": "1500",
            "temperature": "0.8",
        }

        response = requests.post(
            f"{BASE_URL}/system-config/settings/openai",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=settings,
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Successfully saved OpenAI settings:")
            for key, status in result.items():
                print(f"  {key}: {status}")
            return True
        else:
            print(
                f"❌ Failed to save OpenAI settings: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"❌ Error saving OpenAI settings: {e}")
        return False


def test_save_telegram_settings(token):
    """Test saving Telegram settings."""
    print("\n🧪 Testing POST /system-config/settings/telegram...")

    try:
        settings = {
            "bot_token": "test_telegram_token_456",
            "chat_id": "-1001234567890",
            "notifications": "handovers",
        }

        response = requests.post(
            f"{BASE_URL}/system-config/settings/telegram",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=settings,
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Successfully saved Telegram settings:")
            for key, status in result.items():
                print(f"  {key}: {status}")
            return True
        else:
            print(
                f"❌ Failed to save Telegram settings: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"❌ Error saving Telegram settings: {e}")
        return False


def test_save_system_settings(token):
    """Test saving system settings."""
    print("\n🧪 Testing POST /system-config/settings/system...")

    try:
        settings = {
            "name": "Test Boxcatering System",
            "timezone": "Europe/London",
            "language": "en",
            "log_level": "DEBUG",
        }

        response = requests.post(
            f"{BASE_URL}/system-config/settings/system",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=settings,
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Successfully saved system settings:")
            for key, status in result.items():
                print(f"  {key}: {status}")
            return True
        else:
            print(
                f"❌ Failed to save system settings: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"❌ Error saving system settings: {e}")
        return False


def test_save_security_settings(token):
    """Test saving security settings."""
    print("\n🧪 Testing POST /system-config/settings/security...")

    try:
        settings = {
            "jwt_secret": "test_jwt_secret_789",
            "jwt_expiry": "48",
            "password_min_length": "10",
            "session_timeout": "60",
        }

        response = requests.post(
            f"{BASE_URL}/system-config/settings/security",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=settings,
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Successfully saved security settings:")
            for key, status in result.items():
                print(f"  {key}: {status}")
            return True
        else:
            print(
                f"❌ Failed to save security settings: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"❌ Error saving security settings: {e}")
        return False


def test_bulk_settings(token):
    """Test saving multiple settings at once."""
    print("\n🧪 Testing POST /system-config/settings/bulk...")

    try:
        settings = {
            "openai": {"api_key": "bulk_test_openai_key", "model": "gpt-4"},
            "telegram": {
                "bot_token": "bulk_test_telegram_token",
                "notifications": "all",
            },
            "system": {"name": "Bulk Test System", "language": "de"},
        }

        response = requests.post(
            f"{BASE_URL}/system-config/settings/bulk",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=settings,
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Successfully saved bulk settings:")
            for key, status in result.items():
                print(f"  {key}: {status}")
            return True
        else:
            print(
                f"❌ Failed to save bulk settings: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"❌ Error saving bulk settings: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 Starting system configuration API tests...")
    print(f"📍 Testing against: {BASE_URL}")

    # Get authentication token
    print(f"\n🔐 Authenticating as {ADMIN_USERNAME}...")
    token = get_auth_token()

    if not token:
        print("❌ Authentication failed. Cannot proceed with tests.")
        return

    print("✅ Authentication successful!")

    # Run tests
    tests = [
        ("Get All Settings", lambda: test_get_all_settings(token)),
        ("Save OpenAI Settings", lambda: test_save_openai_settings(token)),
        ("Save Telegram Settings", lambda: test_save_telegram_settings(token)),
        ("Save System Settings", lambda: test_save_system_settings(token)),
        ("Save Security Settings", lambda: test_save_security_settings(token)),
        ("Save Bulk Settings", lambda: test_bulk_settings(token)),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print("=" * 50)

        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"💥 {test_name} - ERROR: {e}")

    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! System configuration API is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    main()
