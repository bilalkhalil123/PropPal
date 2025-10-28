"""
Test suite for the Router Agent.
Tests the routing functionality to both Listing and Builder agents.
"""

import os
import sys
from typing import Dict, Any

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Import the RouterAgent
from agents.router_agent import RouterAgent


def print_test_header(test_number: int, description: str):
    """Print a formatted test header."""
    print("\n" + "=" * 70)
    print(f"Test {test_number}: {description}")
    print("=" * 70)


def print_test_result(success: bool, message: str, details: Dict[str, Any] = None):
    """Print test result with formatted output."""
    status = "[✓ PASS]" if success else "[✗ FAIL]"
    print(f"\n{status} {message}")
    
    if details:
        for key, value in details.items():
            if isinstance(value, str) and len(value) > 200:
                print(f"   {key}: {value[:200]}...")
            else:
                print(f"   {key}: {value}")


def test_listing_agent_queries():
    """Test queries that should route to the Listing Agent."""
    print_test_header(1, "Testing Listing Agent Routing")
    
    router = RouterAgent()
    
    # Test queries that should route to listing agent
    listing_queries = [
        {
            "query": "Find houses in Islamabad",
            "description": "Property search query"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(listing_queries, 1):
        print(f"\n{subtest_number(i)} Running: '{test_case['query']}'")
        print(f"   Description: {test_case['description']}")
        
        try:
            result = router.process_query(test_case['query'])
            
            # Check if the query was successful
            if result.get('success'):
                print_test_result(
                    True,
                    f"Query processed successfully",
                    {
                        "classification": result.get('classification'),
                        "response_length": len(result.get('response', '')),
                        "response_preview": result.get('response', '')[:150]
                    }
                )
                
                # Verify it was classified as listing_agent or general_chat
                classification = result.get('classification', '')
                if 'listing' in classification.lower():
                    print(f"   [✓] Correctly routed to Listing Agent")
                    passed += 1
                else:
                    print(f"   [✗] Unexpected classification: {classification}")
                    failed += 1
            else:
                print_test_result(
                    False,
                    f"Query failed",
                    {
                        "error": result.get('error', 'Unknown error'),
                        "response": result.get('response', '')[:100]
                    }
                )
                failed += 1
                
        except Exception as e:
            print_test_result(False, f"Exception occurred: {str(e)}")
            failed += 1
    
    print(f"\n{'-' * 70}")
    print(f"Listing Agent Tests Summary: {passed} passed, {failed} failed")
    return passed, failed


def test_builder_agent_queries():
    """Test queries that should route to the Builder Agent."""
    print_test_header(2, "Testing Builder Agent Routing")
    
    router = RouterAgent()
    
    # Test queries that should route to builder agent
    builder_queries = [
        {
            "query": "Find builders in my area",
            "description": "Builder search query"
        },
        {
            "query": "Show me contractors who do renovation work",
            "description": "Service-based builder search"
        },
        {
            "query": "I need a builder for construction",
            "description": "Builder requirement query"
        },
        {
            "query": "Create a builder profile",
            "description": "Profile creation request"
        },
        {
            "query": "I want to add a new builder service",
            "description": "Service creation request"
        },
        {
            "query": "Who are the best builders in Islamabad?",
            "description": "Builder recommendation query"
        },
        {
            "query": "Find contractors specializing in home renovation",
            "description": "Specialized builder search"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(builder_queries, 1):
        print(f"\n{subtest_number(i)} Running: '{test_case['query']}'")
        print(f"   Description: {test_case['description']}")
        
        try:
            result = router.process_query(
                test_case['query'],
                clerk_id="user_33vwuhpN2VtHHAmSWN0kgq6wPRt"
            )
            
            # Check if the query was successful
            if result.get('success'):
                print_test_result(
                    True,
                    f"Query processed successfully",
                    {
                        "classification": result.get('classification'),
                        "response_length": len(result.get('response', '')),
                        "response_preview": result.get('response', '')[:150]
                    }
                )
                
                # Verify it was classified as builder_agent
                classification = result.get('classification', '')
                if 'builder' in classification.lower():
                    print(f"   [✓] Correctly routed to Builder Agent")
                    passed += 1
                else:
                    print(f"   [✗] Unexpected classification: {classification}")
                    failed += 1
            else:
                print_test_result(
                    False,
                    f"Query failed",
                    {
                        "error": result.get('error', 'Unknown error'),
                        "response": result.get('response', '')[:100]
                    }
                )
                failed += 1
                
        except Exception as e:
            print_test_result(False, f"Exception occurred: {str(e)}")
            failed += 1
    
    print(f"\n{'-' * 70}")
    print(f"Builder Agent Tests Summary: {passed} passed, {failed} failed")
    return passed, failed


def test_general_chat_queries():
    """Test queries that should route to General Chat."""
    print_test_header(3, "Testing General Chat Routing")
    
    router = RouterAgent()
    
    # Test queries that should route to general chat
    general_queries = [
        {
            "query": "Hello, how are you?",
            "description": "Greeting message"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(general_queries, 1):
        print(f"\n{subtest_number(i)} Running: '{test_case['query']}'")
        print(f"   Description: {test_case['description']}")
        
        try:
            result = router.process_query(test_case['query'])
            
            # Check if the query was successful
            if result.get('success'):
                print_test_result(
                    True,
                    f"Query processed successfully",
                    {
                        "classification": result.get('classification'),
                        "response_length": len(result.get('response', '')),
                        "response_preview": result.get('response', '')[:150]
                    }
                )
                
                # Verify it was classified as general_chat
                classification = result.get('classification', '')
                if classification == 'general_chat':
                    print(f"   [✓] Correctly routed to General Chat")
                    passed += 1
                else:
                    print(f"   [✗] Unexpected classification: {classification}")
                    failed += 1
            else:
                print_test_result(
                    False,
                    f"Query failed",
                    {
                        "error": result.get('error', 'Unknown error'),
                        "response": result.get('response', '')[:100]
                    }
                )
                failed += 1
                
        except Exception as e:
            print_test_result(False, f"Exception occurred: {str(e)}")
            failed += 1
    
    print(f"\n{'-' * 70}")
    print(f"General Chat Tests Summary: {passed} passed, {failed} failed")
    return passed, failed


def test_edge_cases():
    """Test edge cases and error handling."""
    print_test_header(4, "Testing Edge Cases and Error Handling")
    
    router = RouterAgent()
    
    edge_cases = [
        {
            "query": "",
            "description": "Empty query"
        },
        {
            "query": "     ",
            "description": "Whitespace only query"
        },
        {
            "query": "Find properties AND builders",
            "description": "Mixed query (property + builder)"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(edge_cases, 1):
        print(f"\n{subtest_number(i)} Running: '{test_case['query']}'")
        print(f"   Description: {test_case['description']}")
        
        try:
            result = router.process_query(test_case['query'])
            
            # For empty queries, we expect failure
            if not test_case['query'].strip():
                if not result.get('success'):
                    print_test_result(True, "Correctly handled empty query")
                    passed += 1
                else:
                    print_test_result(False, "Should have failed on empty query")
                    failed += 1
            else:
                # For other edge cases, just check for success
                if result.get('success'):
                    print_test_result(True, "Query processed")
                    passed += 1
                else:
                    print_test_result(False, "Query failed")
                    failed += 1
                    
        except Exception as e:
            print_test_result(False, f"Exception occurred: {str(e)}")
            failed += 1
    
    print(f"\n{'-' * 70}")
    print(f"Edge Case Tests Summary: {passed} passed, {failed} failed")
    return passed, failed


def subtest_number(n: int) -> str:
    """Format subtest number."""
    return f"  {n}.1"


def run_all_tests():
    """Run all test suites."""
    print("\n" + "=" * 70)
    print("ROUTER AGENT TEST SUITE")
    print("=" * 70)
    print("\nThis test suite verifies that the Router Agent correctly:")
    print("  1. Routes property-related queries to the Listing Agent")
    print("  2. Routes builder-related queries to the Builder Agent")
    print("  3. Routes general queries to General Chat")
    print("  4. Handles edge cases appropriately")
    print("\nNOTE: Make sure you have GROQ_API_KEY set in your environment.")
    print("=" * 70)
    
    # Track total results
    total_passed = 0
    total_failed = 0
    
    # Run test suites
    # passed, failed = test_listing_agent_queries()
    # total_passed += passed
    # total_failed += failed
    
    passed, failed = test_builder_agent_queries()
    total_passed += passed
    total_failed += failed
    
    # passed, failed = test_general_chat_queries()
    # total_passed += passed
    # total_failed += failed
    
    # passed, failed = test_edge_cases()
    # total_passed += passed
    # total_failed += failed
    
    # Print final summary
    print("\n" + "=" * 70)
    print("FINAL TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests Passed: {total_passed}")
    print(f"Total Tests Failed: {total_failed}")
    print(f"Total Tests: {total_passed + total_failed}")
    print(f"Success Rate: {(total_passed / (total_passed + total_failed) * 100):.1f}%")
    print("=" * 70)
    
    if total_failed == 0:
        print("\n[✓] All tests passed!")
    else:
        print(f"\n[✗] {total_failed} test(s) failed")
    
    return total_failed == 0


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[STOP] Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

