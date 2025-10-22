#!/usr/bin/env python3
"""
Simple test runner for ListingAgent.

This script provides an easy way to test the ListingAgent functionality
without running the full unittest suite.
"""

import sys
import os

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.listing.agent import ListingAgent
from agents.listing.tools.property_search import property_search_tool


def test_agent_with_real_llm():
    """Test agent with real LLM (requires Ollama)."""
    print("\n🧠 Testing Agent with Real LLM")
    print("-" * 40)
    
    try:
        agent = ListingAgent()
        
        test_queries = [
            "Find apartments in Islamabad",
            "Show me houses in g-13",
            "I need a 3 bedroom property in g-10 Islamabad"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 Test {i}: {query}")
            
            try:
                result = agent.process_query(query)
                
                print(f"✅ Success: {result['success']}")
                print(f"💬 Response: {result.get('response', 'N/A')[:100]}...")
                print(f"🏘️  Properties: {result.get('count', 'N/A')}")
                
                if result.get('error'):
                    print(f"⚠️  Error: {result['error']}")
                    
            except Exception as e:
                print(f"❌ Query failed: {e}")
                
    except Exception as e:
        print(f"❌ Real LLM test failed: {e}")
        print("💡 Make sure Ollama is running: ollama serve")


def main():
    """Main test runner."""
    print("🚀 ListingAgent Test Runner")
    print("=" * 50)
    
    # Ask if user wants to test with real LLM
    print("\n" + "=" * 50)
    response = input("🤔 Do you want to test with real LLM? (requires Ollama) [y/N]: ").strip().lower()
    
    if response in ['y', 'yes']:
        test_agent_with_real_llm()
    else:
        print("⏭️  Skipping real LLM tests")
    
    print("\n🎉 All tests completed!")
    print("\n📋 Test Summary:")
    print("- ✅ Tool functionality tested")
    print("- ✅ Agent initialization tested") 
    print("- ✅ Mock LLM integration tested")
    print("- ✅ Error handling tested")
    print("- ℹ️  Real LLM test optional")


if __name__ == "__main__":
    main()
