"""
Simple test script for the Chat API endpoint.
Tests the chat functionality using the RouterAgent.
"""

import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_chat_endpoints():
    """Test all chat API endpoints."""
    print("Testing Chat API Endpoints")
    print("=" * 50)
    
    # Test health endpoint
    print("\n1. Testing Health Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/api/chat/health")
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Health check passed: {data['status']}")
            print(f"   Agent: {data['agent_name']}")
            print(f"   Version: {data['version']}")
        else:
            print(f"[ERROR] Health check failed: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Health check error: {e}")
    
    # Test message endpoint
    print("\n2. Testing Message Endpoint")
    test_messages = [
        {
            "message": "Hello, how are you?",
            "expected_classification": "general_chat"
        },
        {
            "message": "Find properties in Islamabad",
            "expected_classification": "listing_agent"
        }
    ]
    
    for i, test in enumerate(test_messages, 1):
        print(f"\n   Test {i}: {test['message']}")
        try:
            payload = {
                "message": test["message"],
                "user_id": f"test_user_{i}",
                "session_id": f"test_session_{i}"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/chat/message",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   [OK] Success: {data['success']}")
                print(f"   Response: {data['response'][:100]}{'...' if len(data['response']) > 100 else ''}")
                print(f"   Classification: {data['classification']}")
                
                # Check if classification matches expectation
                if data['classification'] == test['expected_classification']:
                    print(f"   [OK] Classification correct")
                else:
                    print(f"   [WARNING] Classification mismatch (expected: {test['expected_classification']})")
            else:
                print(f"   [ERROR] Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"   [ERROR] Error: {e}")
    
    print("\n" + "=" * 50)
    print("Chat API testing completed!")


if __name__ == "__main__":
    print("Starting Chat API Tests")
    print("Make sure the FastAPI server is running on http://localhost:8000")
    print("=" * 50)
    
    try:
        test_chat_endpoints()
        print("\n[OK] All tests completed!")
        
    except KeyboardInterrupt:
        print("\n[STOP] Tests interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {e}")
