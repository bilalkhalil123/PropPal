"""
Demo script showing how to use both ListingAgent and RouterAgent.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents import ListingAgent, RouterAgent


def demo_listing_agent():
    """Demo the ListingAgent directly."""
    print("🏠 Demo: ListingAgent (Direct)")
    print("=" * 40)
    
    agent = ListingAgent()
    
    queries = [
        "Find properties in Islamabad under 1 crore",
        "Show me 2 bedroom apartments in i-10 Islamabad"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        result = agent.process_query(query)
        print(f"Success: {result['success']}")
        print(f"Properties found: {result['count']}")
        print(f"Response: {result['response'][:150]}{'...' if len(result['response']) > 150 else ''}")
        if result['properties']:
            print(f"Sample property: {result['properties'][0] if result['properties'] else 'None'}")


def demo_router_agent():
    """Demo the RouterAgent (orchestrator)."""
    print("\n🎯 Demo: RouterAgent (Orchestrator)")
    print("=" * 40)
    
    router = RouterAgent()
    
    queries = [
        "Hello, how are you?",  # Should go to general_chat
        "What is PropPal?",     # Should go to general_chat
        "Find properties in f-10 Islamabad under 50 lakhs",  # Should go to listing_agent
        "Show me houses in g-10 Islamabad under 50 crore",  # Should go to listing_agent
        "How do I create an account?"   # Should go to general_chat
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        result = router.process_query(query)
        print(f"Success: {result['success']}")
        print(f"Classification: {result['classification']}")
        print(f"Response: {result['response'][:150]}{'...' if len(result['response']) > 150 else ''}")


def main():
    """Run the demo."""
    print("🚀 PropPal Agents Demo")
    print("=" * 50)
    
    try:
        # Demo ListingAgent
        demo_listing_agent()
        
        # Demo RouterAgent
        demo_router_agent()
        
        print("\n" + "=" * 50)
        print("✅ Demo completed successfully!")
        print("\nKey Points:")
        print("• ListingAgent: Direct property search functionality")
        print("• RouterAgent: Orchestrator that routes queries to appropriate agents")
        print("• RouterAgent automatically classifies queries and routes them")
        print("• Easy to add new agents in the future!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")


if __name__ == "__main__":
    main()
