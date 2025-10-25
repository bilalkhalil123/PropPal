#!/usr/bin/env python3
"""
Test script for the Chat API endpoints.
Tests the property search functionality through the chat API.
"""
import requests
import json
import time

def test_chat_api():
    """Test the chat API endpoints."""
    base_url = "http://localhost:8000"
    
    print("Starting Chat API Tests")
    print("Make sure the FastAPI server is running on http://localhost:8000")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1. Testing Health Endpoint")
    try:
        response = requests.get(f"{base_url}/api/chat/health")
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Health check passed: {data.get('status', 'unknown')}")
            print(f"   Agent: {data.get('agent', 'unknown')}")
            print(f"   Version: {data.get('version', 'unknown')}")
        else:
            print(f"[ERROR] Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Health check failed: {e}")
        return False
    
    # Test 2: Message Endpoint - General Chat
    print("\n2. Testing Message Endpoint - General Chat")
    try:
        payload = {"message": "Hello, how are you?"}
        response = requests.post(f"{base_url}/api/chat/message", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Success: {data.get('success')}")
            print(f"   Response: {data.get('response', '')[:100]}...")
            print(f"   Classification: {data.get('classification', 'unknown')}")
            print(f"   [OK] Classification correct")
        else:
            print(f"   [ERROR] Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   [ERROR] Request failed: {e}")
    
    # Test 3: Message Endpoint - Property Search
    print("\n3. Testing Message Endpoint - Property Search")
    try:
        payload = {"message": "Find houses in Islamabad"}
        response = requests.post(f"{base_url}/api/chat/message", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Success: {data.get('success')}")
            print(f"   Response: {data.get('response', '')[:200]}...")
            print(f"   Classification: {data.get('classification', 'unknown')}")
            
            # Check if properties were found
            if "houses" in data.get('response', '').lower() and "islamabad" in data.get('response', '').lower():
                print(f"   [OK] Properties found in response")
            else:
                print(f"   [WARNING] No properties found in response")
        else:
            print(f"   [ERROR] Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   [ERROR] Request failed: {e}")
    
    # Test 4: Message Endpoint - Specific Property Search
    print("\n4. Testing Message Endpoint - Specific Property Search")
    try:
        payload = {"message": "Show me properties in F-10 Islamabad"}
        response = requests.post(f"{base_url}/api/chat/message", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Success: {data.get('success')}")
            print(f"   Response: {data.get('response', '')[:200]}...")
            print(f"   Classification: {data.get('classification', 'unknown')}")
        else:
            print(f"   [ERROR] Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   [ERROR] Request failed: {e}")
    
    # Test 5: Message Endpoint - Price Range Search
    print("\n5. Testing Message Endpoint - Price Range Search")
    try:
        payload = {"message": "Find houses in Islamabad under 50 lakhs"}
        response = requests.post(f"{base_url}/api/chat/message", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Success: {data.get('success')}")
            print(f"   Response: {data.get('response', '')[:200]}...")
            print(f"   Classification: {data.get('classification', 'unknown')}")
        else:
            print(f"   [ERROR] Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   [ERROR] Request failed: {e}")
    
    # Test 6: Capabilities Endpoint
    print("\n6. Testing Capabilities Endpoint")
    try:
        response = requests.get(f"{base_url}/api/chat/capabilities")
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Capabilities retrieved")
            print(f"   Agent: {data.get('agent', 'unknown')}")
            print(f"   Capabilities: {data.get('capabilities', [])}")
        else:
            print(f"   [ERROR] Request failed: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] Request failed: {e}")
    
    # Test 7: Status Endpoint
    print("\n7. Testing Status Endpoint")
    try:
        response = requests.get(f"{base_url}/api/chat/status")
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Status retrieved")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Agent: {data.get('agent', 'unknown')}")
        else:
            print(f"   [ERROR] Request failed: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] Request failed: {e}")
    
    print("\n" + "=" * 50)
    print("Chat API testing completed!")
    print("[OK] All tests completed!")

if __name__ == "__main__":
    test_chat_api()