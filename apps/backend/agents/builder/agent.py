"""
Main Builder Agent - Acts as a sub-router for all builder-related tasks.

This agent classifies the user's intent and routes the query to the
appropriate sub-agent (e.g., Search, Profile Creation, Service Creation).
"""
import logging
from typing import Any, Dict, Literal

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from .search_agent import BuilderSearchAgent
from .create_service_agent import BuilderServiceCreationAgent
from .create_profile_agent import BuilderProfileCreationAgent

load_dotenv()


class BuilderRoute(BaseModel):
    """Select the appropriate sub-agent for the user's query about builders."""
    destination: Literal["search", "create_profile", "create_service", "general"] = Field(
        description="The type of task the user wants to perform. 'search' for finding builders/services, 'create_profile' for making a builder profile, 'create_service' for adding a new service, and 'general' for anything else.",
        default="general"
    )


class BuilderAgent:
    """
    A router agent that delegates tasks to specialized builder sub-agents.
    """

    def __init__(self):
        # The router LLM decides which sub-agent to use.
        self.router_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.1
        ).with_structured_output(BuilderRoute)

        # Instantiate all the sub-agents this router can delegate to.
        self.search_agent = BuilderSearchAgent()
        self.service_creation_agent = BuilderServiceCreationAgent()
        self.profile_creation_agent = BuilderProfileCreationAgent()


    def process_query(self, query: str, clerk_id: str = None) -> Dict[str, Any]:
        """
        Processes a builder-related query by first classifying the intent
        and then routing to the appropriate sub-agent.

        Args:
            clerk_id: The ID of the user, required for creation tasks.
        """
        if not query or not query.strip():
            return {
                "success": False,
                "response": "Please provide a valid query.",
                "classification": "error",
                "error": "Empty query provided"
            }

        # 1. Classify the intent using the router LLM
        try:
            route = self.router_llm.invoke([HumanMessage(content=query)])
            destination = route.destination
        except Exception as e:
            destination = "general" # Default to general on failure

        # 2. Route to the appropriate sub-agent based on the classification
        if destination == "search":
            result = self.search_agent.process_query(query)
            result["classification"] = "builder_search"
            return result

        if destination == "create_service":
            result = self.service_creation_agent.process_query(query, clerk_id=clerk_id)
            result["classification"] = "builder_create_service"
            return result

        if destination == "create_profile":
            result = self.profile_creation_agent.process_query(query, clerk_id=clerk_id)
            result["classification"] = "builder_create_profile"
            return result

        # Default to a general response if no specific route is matched
        return {
            "success": True,
            "response": "I can help with finding builders and their services. How can I assist you with that today?",
            "classification": "builder_general",
            "properties": [],
            "count": 0,
            "error": None
        }
