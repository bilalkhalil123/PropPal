"""
Demo script for testing the BuilderAgent and its sub-agents.
"""

import sys
import os
import logging
import json

# Add the current directory ('backend') to Python's path
# This allows imports like 'from agents...' and 'from services...' to work.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file at the very beginning
from dotenv import load_dotenv
load_dotenv()


from agents import BuilderAgent
from agents.listing.agent import AgentState

def demo_builder_agent():
    """Demo the BuilderAgent directly."""
    print("👷 Demo: BuilderAgent (Sub-Router)")
    print("=" * 50)
    
    agent = BuilderAgent()
    
    queries = [
        # Should route to search_agent and use builder_profile_search_tool
        "Find me construction companies in Islamabad",
        # Should route to search_agent and use builder_service_search_tool
        "I need someone for roof repair",
        # Should be handled by the builder agent's general response
        "How does this work?",
        # A more specific profile search
        "Show me builders who specialize in residential homes",
        # A more specific service search
        "who can do plumbing work for a new bathroom"
    ]
    
    for query in queries:
        print(f"\n--- Query: '{query}' ---")
        try:
            result = agent.process_query(query)
        except Exception as e:
            print(f"An error occurred while processing the query: {e}")
            logging.exception("Query processing failed.")
            
def demo_service_creation_conversation():
    """Demo the conversational profile creation agent."""
    print("\n\n👷 Demo: Builder Profile Creation (Interactive Chat)")
    print("=" * 50)
    
    agent = BuilderAgent()
    # Use a fake clerk_id to simulate a new user without a profile.
    # This allows us to test the creation flow without being blocked by the
    # "profile already exists" check. The tool call will fail at the end
    # because the user doesn't exist, which is expected for this test.
    mock_clerk_id_new_user = "user_33vOLh0XjHaBocHDxtEtHfxaUcm"
    # The agent will now guide you through the creation process interactively.
    result = agent.process_query(query="I want to create a builder service", clerk_id=mock_clerk_id_new_user)

def demo_profile_creation_conversation():
    """Demo the conversational profile creation agent."""
    print("\n\n👷 Demo: BuilderProfileCreationAgent (Conversational)")
    print("=" * 50)
    
    agent = BuilderAgent()
    
    # Use a different mock ID to simulate a new user without a profile
    mock_clerk_id_new_user = "user_new_profile_test_12345"
    
    # This conversation will gather all info and call the tool
    full_conversation_query = """
    User: I want to create a builder profile.
    Agent: I can help with that! To get started, what is the name of your company?
    User: Apex Builders
    Agent: Great name! What are your areas of specialization? You can list a few, like 'residential construction, commercial development'.
    User: residential construction, kitchen remodeling
    Agent: Perfect. How many years of experience do you have in the industry?
    User: 15
    Agent: Excellent. Now, please provide a brief 'about us' description for your profile.
    User: We are a family-owned business dedicated to quality craftsmanship and customer satisfaction.
    Agent: That sounds great. Lastly, what is the primary city you operate in?
    User: Islamabad
    """
    print(f"\n--- Simulating a full profile creation conversation ---")
    result = agent.process_query(query=full_conversation_query, clerk_id=mock_clerk_id_new_user)
    print(f"--- Agent Final Response: {result['response']} ---")
    print(f"--- Success: {result.get('success', 'N/A')}, Classification: {result.get('classification', 'N/A')}, Error: {result.get('error')} ---")

def main():
    """Run the demo."""
    # demo_builder_agent()
    demo_service_creation_conversation() # You can create this function for service creation demo
    # demo_profile_creation_conversation()

if __name__ == "__main__":
    main()
