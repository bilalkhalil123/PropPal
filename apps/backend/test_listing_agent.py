"""
Simple test file for the ListingAgent.
Tests various scenarios to ensure the agent works properly.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents import ListingAgent


def test_agent():
    """Test the ListingAgent with various scenarios."""
    print("🧪 Testing ListingAgent...")
    print("=" * 50)
    
    # Initialize the agent
    try:
        agent = ListingAgent()
        print("✅ Agent initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return False
    
    # Test cases
    test_cases = [
        {
            "name": "Empty Query",
            "query": "",
            "expected_success": False,
            "expected_error": "Empty query provided"
        },
        {
            "name": "Whitespace Only Query",
            "query": "   ",
            "expected_success": False,
            "expected_error": "Empty query provided"
        },
        {
            "name": "General Question",
            "query": "Hello, how are you?",
            "expected_success": True,
            "expected_error": None
        },
        {
            "name": "Property Search Query",
            "query": "Find me a 3 bedroom house in Islamabad under 50 lakhs",
            "expected_success": True,  # Should succeed with API running
            "expected_error": None
        },
        {
            "name": "Property Search with Specifics",
            "query": "I need a 3 bedroom house in Islamabad under 100 lakhs",
            "expected_success": True,  # Should succeed with API running
            "expected_error": None
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"Query: '{test_case['query']}'")
        
        try:
            result = agent.process_query(test_case['query'])
            
            # Check success status
            if result['success'] == test_case['expected_success']:
                print(f"✅ Success status correct: {result['success']}")
            else:
                print(f"❌ Success status incorrect. Expected: {test_case['expected_success']}, Got: {result['success']}")
                continue
            
            # Check error message for empty queries
            if test_case['expected_error']:
                if result.get('error') == test_case['expected_error']:
                    print(f"✅ Error message correct: {result['error']}")
                else:
                    print(f"❌ Error message incorrect. Expected: {test_case['expected_error']}, Got: {result.get('error')}")
                    continue
            
            # Check response content
            if result['response']:
                print(f"✅ Response generated: {result['response'][:100]}{'...' if len(result['response']) > 100 else ''}")
            else:
                print("❌ No response generated")
                continue
            
            # Show properties data if available
            if result.get('properties') and len(result['properties']) > 0:
                print(f"🏠 Properties found: {result['count']} properties")
                print(f"📊 Properties data: {result['properties'][:2]}{'...' if len(result['properties']) > 2 else ''}")
            elif result.get('count', 0) == 0 and 'property' in test_case['query'].lower():
                print("ℹ️  No properties found (this is expected for some queries)")
            else:
                print(f"📊 Properties count: {result.get('count', 0)}")
            
            # Check data structure
            required_keys = ['success', 'response', 'properties', 'count', 'error']
            if all(key in result for key in required_keys):
                print("✅ Response structure correct")
            else:
                print(f"❌ Response structure incorrect. Missing keys: {[key for key in required_keys if key not in result]}")
                continue
            
            print("✅ Test passed!")
            passed_tests += 1
            
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The ListingAgent is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False


def test_property_search():
    """Test property search functionality specifically."""
    print("\n🏠 Testing Property Search...")
    print("=" * 40)
    
    try:
        agent = ListingAgent()
        
        # Test property search queries
        property_queries = [
            "Find properties in i-10 Islamabad under 1 crore",
            "Show me houses in G-10 Islamabad under 1 crore",
            "I need a 2 bedroom apartment in i-10 Islamabad"
        ]
        
        for i, query in enumerate(property_queries, 1):
            print(f"\n🔍 Property Search Test {i}:")
            print(f"Query: '{query}'")
            
            result = agent.process_query(query)
            
            print(f"Success: {result['success']}")
            print(f"Response: {result['response']}")
            print(f"Properties Count: {result['count']}")
            
            if result['success'] and result['count'] > 0:
                print(f"🏠 Found {result['count']} properties!")
                print("📋 Properties Data:")
                for j, prop in enumerate(result['properties'][:3], 1):  # Show first 3 properties
                    print(f"  Property {j}: {prop}")
                if len(result['properties']) > 3:
                    print(f"  ... and {len(result['properties']) - 3} more properties")
            elif result['success'] and result['count'] == 0:
                print("ℹ️  No properties found for this query")
            else:
                print(f"❌ Search failed: {result.get('error', 'Unknown error')}")
        
        print("\n✅ Property search tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Property search test failed: {e}")
        return False


def test_agent_properties():
    """Test specific agent properties and methods."""
    print("\n🔍 Testing Agent Properties...")
    print("=" * 30)
    
    try:
        agent = ListingAgent()
        
        # Test agent attributes
        assert hasattr(agent, 'name'), "Agent should have a name attribute"
        assert hasattr(agent, 'tools'), "Agent should have tools attribute"
        assert hasattr(agent, 'llm'), "Agent should have llm attribute"
        assert hasattr(agent, 'app'), "Agent should have app attribute"
        
        print("✅ Agent has all required attributes")
        
        # Test agent name
        assert agent.name == "ListingAgent", f"Expected name 'ListingAgent', got '{agent.name}'"
        print("✅ Agent name is correct")
        
        # Test tools
        assert len(agent.tools) == 1, f"Expected 1 tool, got {len(agent.tools)}"
        print("✅ Agent has correct number of tools")
        
        print("✅ All property tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Property test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Starting ListingAgent Tests")
    print("=" * 50)
    
    # Run tests
    agent_tests_passed = test_agent()
    property_search_passed = test_property_search()
    property_tests_passed = test_agent_properties()
    
    # Final result
    print("\n" + "=" * 50)
    if agent_tests_passed and property_search_passed and property_tests_passed:
        print("🎉 ALL TESTS PASSED! The ListingAgent is working perfectly.")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED! Please check the output above.")
        sys.exit(1)
