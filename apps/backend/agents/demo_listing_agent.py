#!/usr/bin/env python3
"""
Demo script for ListingAgent.

This script demonstrates the ListingAgent capabilities with various
property search queries and shows the tool classification in action.
"""

import sys
import os
import time

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.listing.agent import ListingAgent


def print_separator(title=""):
    """Print a visual separator."""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print(f"\n{'-'*60}")


def print_result(result, query):
    """Print formatted result."""
    print(f"\n📝 Query: {query}")
    print(f"✅ Success: {result['success']}")
    print(f"💬 Response: {result['response']}")
    print(f"🏘️  Properties Found: {result['count']}")
    
    if result.get('error'):
        print(f"❌ Error: {result['error']}")
    
    if result.get('properties') and len(result['properties']) > 0:
        print(f"📋 Sample Properties:")
        for i, prop in enumerate(result['properties'][:3], 1):  # Show first 3
            print(f"   {i}. {prop.get('title', 'Unknown Title')}")
            if prop.get('location'):
                print(f"      Location: {prop['location']}")
            if prop.get('price'):
                print(f"      Price: {prop['price']:,} PKR")
            if prop.get('bedrooms'):
                print(f"      Bedrooms: {prop['bedrooms']}")


def demo_basic_queries():
    """Demo basic property search queries."""
    print_separator("Basic Property Search Queries")
    
    agent = ListingAgent()
    
    basic_queries = [
        "Find apartments in Islamabad",
        "Show me houses in Karachi",
        "I need a 3 bedroom property",
        "Looking for commercial space",
        "Villa under 1 crore"
    ]
    
    for query in basic_queries:
        try:
            result = agent.process_query(query)
            print_result(result, query)
            time.sleep(1)  # Small delay for readability
        except Exception as e:
            print(f"\n❌ Query failed: {query}")
            print(f"   Error: {e}")


def demo_location_queries():
    """Demo location-specific queries."""
    print_separator("Location-Specific Queries")
    
    agent = ListingAgent()
    
    location_queries = [
        "Properties in F-8 Islamabad",
        "Houses in DHA Karachi",
        "Apartments in Gulberg Lahore",
        "Commercial property in Rawalpindi",
        "Plots in Bahria Town"
    ]
    
    for query in location_queries:
        try:
            result = agent.process_query(query)
            print_result(result, query)
            time.sleep(1)
        except Exception as e:
            print(f"\n❌ Query failed: {query}")
            print(f"   Error: {e}")


def demo_price_queries():
    """Demo price-based queries."""
    print_separator("Price-Based Queries")
    
    agent = ListingAgent()
    
    price_queries = [
        "Properties under 50 lakh",
        "Houses between 1-2 crore",
        "Apartments under 30 lakh",
        "Commercial space under 1 crore",
        "Budget-friendly properties"
    ]
    
    for query in price_queries:
        try:
            result = agent.process_query(query)
            print_result(result, query)
            time.sleep(1)
        except Exception as e:
            print(f"\n❌ Query failed: {query}")
            print(f"   Error: {e}")


def demo_property_type_queries():
    """Demo property type-specific queries."""
    print_separator("Property Type Queries")
    
    agent = ListingAgent()
    
    type_queries = [
        "2 bedroom apartments",
        "3 bedroom houses",
        "Studio apartments",
        "Penthouse for rent",
        "Office space for sale",
        "Warehouse properties",
        "Farm houses",
        "Duplex houses"
    ]
    
    for query in type_queries:
        try:
            result = agent.process_query(query)
            print_result(result, query)
            time.sleep(1)
        except Exception as e:
            print(f"\n❌ Query failed: {query}")
            print(f"   Error: {e}")


def demo_conversational_queries():
    """Demo conversational queries."""
    print_separator("Conversational Queries")
    
    agent = ListingAgent()
    
    conversational_queries = [
        "Hi, I'm looking for a new home",
        "Can you help me find a place to live?",
        "I need something affordable in a good area",
        "What properties do you have available?",
        "I'm interested in buying my first house",
        "Show me some options please"
    ]
    
    for query in conversational_queries:
        try:
            result = agent.process_query(query)
            print_result(result, query)
            time.sleep(1)
        except Exception as e:
            print(f"\n❌ Query failed: {query}")
            print(f"   Error: {e}")


def demo_error_handling():
    """Demo error handling scenarios."""
    print_separator("Error Handling Scenarios")
    
    agent = ListingAgent()
    
    error_queries = [
        "",  # Empty query
        "a" * 1000,  # Very long query
        "!@#$%^&*()",  # Special characters only
        "Find apartments in nonexistentcity123",  # Invalid location
        "Show me properties with 999 bedrooms"  # Unrealistic criteria
    ]
    
    for query in error_queries:
        try:
            result = agent.process_query(query)
            print_result(result, query)
            time.sleep(1)
        except Exception as e:
            print(f"\n❌ Query failed: {query[:50]}...")
            print(f"   Error: {e}")


def demo_tool_classification():
    """Demo tool classification capabilities."""
    print_separator("Tool Classification Demo")
    
    agent = ListingAgent()
    
    # Show how the agent classifies different queries
    classification_queries = [
        "Find apartments in Islamabad",
        "Hello, how are you?",
        "What is the weather like?",
        "Show me properties in Karachi",
        "I need help with my account"
    ]
    
    for query in classification_queries:
        print(f"\n📝 Query: {query}")
        
        try:
            # Test classification directly
            catalog = agent._build_tool_catalog()
            prompt = agent._create_classification_prompt(query, catalog)
            
            print(f"🔧 Available tools: {[tool['name'] for tool in catalog]}")
            print(f"📋 Classification prompt length: {len(prompt)} characters")
            
            # Show what the LLM would receive
            print(f"🎯 Expected tool selection: property_search_tool")
            
        except Exception as e:
            print(f"❌ Classification test failed: {e}")


def interactive_demo():
    """Interactive demo where user can input queries."""
    print_separator("Interactive Demo")
    
    agent = ListingAgent()
    
    print("🎮 Interactive Property Search Demo")
    print("Type your property search queries (or 'quit' to exit)")
    print("Examples:")
    print("  - Find apartments in Islamabad")
    print("  - Show me houses in Karachi")
    print("  - I need a 3 bedroom property")
    print("  - Commercial space under 1 crore")
    
    while True:
        try:
            query = input("\n🔍 Enter your query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not query:
                print("⚠️  Please enter a query")
                continue
            
            print(f"\n⏳ Processing: {query}")
            result = agent.process_query(query)
            print_result(result, query)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """Main demo function."""
    print("🏠 ListingAgent Demo")
    print("=" * 60)
    print("This demo shows the ListingAgent capabilities with various queries.")
    print("Make sure Ollama is running: ollama serve")
    
    try:
        # Run all demo sections
        demo_basic_queries()
        demo_location_queries()
        demo_price_queries()
        demo_property_type_queries()
        demo_conversational_queries()
        demo_error_handling()
        demo_tool_classification()
        
        # Ask if user wants interactive demo
        print_separator()
        response = input("🎮 Would you like to try the interactive demo? [y/N]: ").strip().lower()
        
        if response in ['y', 'yes']:
            interactive_demo()
        else:
            print("⏭️  Skipping interactive demo")
        
        print_separator("Demo Complete")
        print("🎉 Thank you for trying the ListingAgent demo!")
        print("📋 Summary of capabilities demonstrated:")
        print("  ✅ Basic property search")
        print("  ✅ Location-specific queries")
        print("  ✅ Price-based filtering")
        print("  ✅ Property type queries")
        print("  ✅ Conversational queries")
        print("  ✅ Error handling")
        print("  ✅ Tool classification")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("💡 Make sure Ollama is running: ollama serve")


if __name__ == "__main__":
    main()

