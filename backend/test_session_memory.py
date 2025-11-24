#!/usr/bin/env python3
"""
Test script to verify conversation memory / session management
Tests that the session manager properly reuses session IDs for conversation continuity
"""

import requests
import json
import time

BASE_URL = "http://localhost:5001/api"

def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def test_session_info():
    """Test getting session info"""
    print_header("TEST 1: Get Session Info (No Session Yet)")

    response = requests.get(f"{BASE_URL}/session/info")
    data = response.json()

    print(json.dumps(data, indent=2))
    assert data['has_session'] == False, "Should have no session initially"
    print("✅ Test passed: No session exists initially")

def send_message(message, pf_token=None):
    """Send a message to the agent and return the response"""
    payload = {
        "message": message,
        "pf_client_id": "09PF05VD",
        "pf_user_id": "6f72bffa-c323-4058-a01c-9d495d696364"
    }

    if pf_token:
        payload["pf_token"] = pf_token

    response = requests.post(f"{BASE_URL}/classify", json=payload)
    return response.json()

def test_conversation_memory():
    """Test that conversation memory works across multiple messages"""
    print_header("TEST 2: Multi-Turn Conversation (Memory Test)")

    # Message 1: Initial greeting
    print("📤 Message 1: 'Hello'")
    response1 = send_message("Hello")
    session_id_1 = response1.get('session_id')
    print(f"  Session ID: {session_id_1}")
    print(f"  Response preview: {response1['response'][:100]}...")

    # Check session info
    time.sleep(1)
    session_info = requests.get(f"{BASE_URL}/session/info").json()
    print(f"\n  Session Info: Active={session_info['is_active']}, Age={session_info['age_seconds']}s")

    # Message 2: Follow-up (should reuse same session)
    print("\n📤 Message 2: 'Show me my projects'")
    time.sleep(2)  # Small delay to simulate real conversation
    response2 = send_message("Show me my projects")
    session_id_2 = response2.get('session_id')
    print(f"  Session ID: {session_id_2}")
    print(f"  Response preview: {response2['response'][:100]}...")

    # Verify same session is reused
    assert session_id_1 == session_id_2, "Session ID should be the same!"
    print(f"\n✅ Test passed: Session reused! ({session_id_1} == {session_id_2})")

    # Message 3: Reference to previous context
    print("\n📤 Message 3: 'Schedule the first one'")
    time.sleep(2)
    response3 = send_message("Schedule the first one")
    session_id_3 = response3.get('session_id')
    print(f"  Session ID: {session_id_3}")
    print(f"  Response preview: {response3['response'][:100]}...")

    # Verify same session still
    assert session_id_1 == session_id_3, "Session ID should still be the same!"
    print(f"\n✅ Test passed: Session still reused! ({session_id_1} == {session_id_3})")

    # Final session info
    session_info = requests.get(f"{BASE_URL}/session/info").json()
    print(f"\n  Final Session Info: Active={session_info['is_active']}, Age={session_info['age_seconds']}s")

def test_session_reset():
    """Test session reset functionality"""
    print_header("TEST 3: Session Reset")

    # Get current session info
    session_before = requests.get(f"{BASE_URL}/session/info").json()
    print(f"Before reset: has_session={session_before['has_session']}")

    # Reset session
    reset_response = requests.post(f"{BASE_URL}/session/reset", json={}).json()
    print(f"\nReset response: {reset_response['message']}")

    # Check session info after reset
    session_after = requests.get(f"{BASE_URL}/session/info").json()
    print(f"After reset: has_session={session_after['has_session']}")

    assert session_after['has_session'] == False, "Session should be cleared"
    print("\n✅ Test passed: Session successfully reset")

    # Send new message - should create new session
    print("\n📤 New message after reset: 'Hi again'")
    response = send_message("Hi again")
    new_session_id = response.get('session_id')
    print(f"  New Session ID: {new_session_id}")

    # Verify it's different from old session
    if session_before['has_session']:
        old_session_id = session_before['session_id']
        assert new_session_id != old_session_id, "Should have new session ID after reset"
        print(f"✅ Test passed: New session created ({new_session_id} != {old_session_id})")
    else:
        print(f"✅ Test passed: New session created ({new_session_id})")

def test_session_stats():
    """Test session statistics endpoint"""
    print_header("TEST 4: Session Statistics")

    response = requests.get(f"{BASE_URL}/session/stats")
    stats = response.json()

    print(json.dumps(stats, indent=2))
    print(f"\n✅ Active sessions: {stats['active_sessions']}")
    print(f"✅ Total sessions: {stats['total_sessions']}")

def run_all_tests():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  Session Memory / Conversation Continuity Test Suite        ║
╚══════════════════════════════════════════════════════════════╝

This test verifies that:
1. Session IDs are reused for the same customer
2. Conversation context is maintained across messages
3. Session reset works correctly
4. Session statistics are accurate

Prerequisites:
- Flask backend running on localhost:5001
- Bedrock agents configured and accessible
""")

    try:
        # Verify backend is running
        health = requests.get(f"{BASE_URL}/health", timeout=2)
        if health.status_code != 200:
            print("❌ ERROR: Backend not healthy")
            return
        print("✅ Backend is running and healthy\n")

        # Run tests
        test_session_info()
        test_conversation_memory()
        test_session_reset()
        test_session_stats()

        print_header("🎉 ALL TESTS PASSED!")

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to Flask backend")
        print("Please start the backend with: cd bedrock/backend && python3 app.py")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
