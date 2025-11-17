"""
Builder Agent - LangGraph sub-router for builder-related tasks.

This agent acts as a router/orchestrator for builder-related queries.
It classifies the query and routes to specialized agents:
- BuilderSearchAgent: For searching builders and services
- BuilderProfileCreationAgent: For creating builder profiles (interactive)
- BuilderServiceCreationAgent: For creating builder services (interactive)

The BuilderAgent does NOT perform the specialized work itself.
It only routes queries to the appropriate specialized agent.
"""
import logging
import os
from typing import Any, Dict, List, Literal, Optional, TypedDict, Annotated
import operator

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import StateGraph, END

from .search_agent import BuilderSearchAgent
from .create_service_agent import BuilderServiceCreationAgent
from .create_profile_agent import BuilderProfileCreationAgent

load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================
# State Definition for BuilderAgent LangGraph
# ============================================================

class BuilderState(TypedDict):
    """State for the BuilderAgent graph."""
    query: str
    clerk_id: Optional[str]
    classification: Optional[str]
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Results from specialized agents
    builders: List[Dict[str, Any]]
    services: List[Dict[str, Any]]
    
    # Metadata for interactive sessions
    metadata: Optional[Dict[str, Any]]
    
    # Error tracking
    error: Optional[str]


# ============================================================
# Classification Model
# ============================================================

class BuilderRoutePlan(BaseModel):
    """Structured classification for builder requests."""
    task: Literal["search", "create_profile", "create_service"] = Field(
        description="The primary task inferred from the query."
    )


# ============================================================
# Graph Nodes
# ============================================================

def classify_builder_query_node(state: BuilderState) -> Dict[str, Any]:
    """
    Classify the builder query into one of:
    - search: Search for builders or services
    - create_profile: Create a builder profile
    - create_service: Create a builder service
    """
    logger.info("--- [BuilderAgent] Classifying Query ---")
    query = state.get("query", "")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a classifier for builder-related queries. Classify the user's query into ONE of these tasks:\n"
            "- 'search': If they want to find/search for builders, contractors, or services\n"
            "- 'create_profile': If they want to create/register a builder profile or become a builder\n"
            "- 'create_service': If they want to add/create a new service offering\n\n"
            "Examples:\n"
            "- 'find plumbers in Lahore' -> search\n"
            "- 'I want to register as a builder' -> create_profile\n"
            "- 'add a new service' -> create_service\n"
            "- 'create my builder account' -> create_profile\n"
            "- 'I offer painting services' -> create_service"
        )),
        ("human", "{query}")
    ])
    
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0,
    ).with_structured_output(BuilderRoutePlan)
    
    chain = prompt | llm
    
    try:
        result = chain.invoke({"query": query})
        classification = result.task
        logger.info(f"--- [BuilderAgent] Classification: {classification} ---")
        return {"classification": classification}
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return {"classification": "search", "error": f"Classification error: {str(e)}"}


def route_to_task(state: BuilderState) -> str:
    """Conditional edge function to route to the appropriate node."""
    classification = state.get("classification", "search")
    
    if classification == "search":
        return "search_node"
    elif classification == "create_profile":
        return "create_profile_node"
    elif classification == "create_service":
        return "create_service_node"
    else:
        return "search_node"  # Default fallback


def search_node(state: BuilderState) -> Dict[str, Any]:
    """
    Route to BuilderSearchAgent for searching builders/services.
    This agent does the actual search work.
    """
    logger.info("--- [BuilderAgent] Routing to BuilderSearchAgent ---")
    query = state.get("query", "")
    
    try:
        search_agent = BuilderSearchAgent()
        result = search_agent.process_query(query)
        
        response_message = result.get("response", "Search completed.")
        builders = result.get("builders", [])
        services = result.get("services", [])
        
        return {
            "messages": [AIMessage(content=response_message)],
            "builders": builders,
            "services": services,
        }
    except Exception as e:
        logger.error(f"Search node failed: {e}", exc_info=True)
        return {
            "messages": [AIMessage(content=f"Search failed: {str(e)}")],
            "error": str(e),
        }


def create_profile_node(state: BuilderState) -> Dict[str, Any]:
    """
    Signal that profile creation should start in interactive mode.
    The WebSocket handler will detect this and start the interactive session.
    """
    logger.info("--- [BuilderAgent] Profile Creation Requested ---")
    
    clerk_id = state.get("clerk_id")
    if not clerk_id:
        return {
            "messages": [AIMessage(content="I need your user ID to create a profile. Please log in first.")],
            "error": "Missing clerk_id for profile creation",
        }
    
    # Return metadata to signal interactive mode should start
    return {
        "messages": [AIMessage(content="Great! I'll guide you through creating your builder profile. I'll ask for the necessary details one by one.")],
        "metadata": {
            "interactive_mode": True,
            "agent_type": "profile",
            "clerk_id": clerk_id,
        }
    }


def create_service_node(state: BuilderState) -> Dict[str, Any]:
    """
    Signal that service creation should start in interactive mode.
    The WebSocket handler will detect this and start the interactive session.
    """
    logger.info("--- [BuilderAgent] Service Creation Requested ---")
    
    clerk_id = state.get("clerk_id")
    if not clerk_id:
        return {
            "messages": [AIMessage(content="I need your user ID to create a service. Please log in first.")],
            "error": "Missing clerk_id for service creation",
        }
    
    # Return metadata to signal interactive mode should start
    return {
        "messages": [AIMessage(content="Perfect! I'll start the interactive flow to capture your service details.")],
        "metadata": {
            "interactive_mode": True,
            "agent_type": "service",
            "clerk_id": clerk_id,
        }
    }


# ============================================================
# Build the LangGraph
# ============================================================

def create_builder_graph():
    """Create and return the compiled BuilderAgent graph."""
    workflow = StateGraph(BuilderState)
    
    # Add nodes
    workflow.add_node("classifier", classify_builder_query_node)
    workflow.add_node("search_node", search_node)
    workflow.add_node("create_profile_node", create_profile_node)
    workflow.add_node("create_service_node", create_service_node)
    
    # Set entry point
    workflow.set_entry_point("classifier")
    
    # Add conditional edges from classifier
    workflow.add_conditional_edges(
        "classifier",
        route_to_task,
        {
            "search_node": "search_node",
            "create_profile_node": "create_profile_node",
            "create_service_node": "create_service_node",
        }
    )
    
    # All nodes end after execution
    workflow.add_edge("search_node", END)
    workflow.add_edge("create_profile_node", END)
    workflow.add_edge("create_service_node", END)
    
    return workflow.compile()


builder_agent_app = create_builder_graph()


# ============================================================
# Public API
# ============================================================

class BuilderAgent:
    """
    Public interface for the BuilderAgent.
    Routes builder-related queries to specialized agents.
    """
    
    def __init__(self):
        self.app = builder_agent_app
        self.name = "BuilderAgent"
    
    def process_query(self, query: str, clerk_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a builder-related query.
        
        Args:
            query: The user's query
            clerk_id: The user's clerk_id (required for creation tasks)
        
        Returns:
            Dict with:
            - success: bool
            - response: str (the agent's response)
            - classification: str (the task type)
            - builders: list (for search results)
            - services: list (for search results)
            - metadata: dict (for interactive mode signals)
            - error: str (if any error occurred)
        """
        if not query or not query.strip():
            return {
                "success": False,
                "response": "Please provide a valid query.",
                "classification": "error",
                "error": "Empty query provided",
            }
        
        try:
            # Initialize state
            initial_state: BuilderState = {
                "query": query.strip(),
                "clerk_id": clerk_id,
                "classification": None,
                "messages": [],
                "builders": [],
                "services": [],
                "metadata": None,
                "error": None,
            }
            
            # Run the graph
            final_state = self.app.invoke(initial_state)
            
            # Extract results
            messages: List[BaseMessage] = final_state.get("messages", [])
            response_content = messages[-1].content if messages else "I can help you with builder searches, profile creation, or service creation."
            
            classification = final_state.get("classification", "unknown")
            builders = final_state.get("builders", [])
            services = final_state.get("services", [])
            metadata = final_state.get("metadata")
            error = final_state.get("error")
            
            return {
                "success": not bool(error),
                "response": response_content,
                "classification": classification,
                "builders": builders,
                "services": services,
                "metadata": metadata,
                "error": error,
            }
            
        except Exception as e:
            logger.error(f"BuilderAgent failed: {e}", exc_info=True)
            return {
                "success": False,
                "response": f"An error occurred: {str(e)}",
                "classification": "error",
                "error": str(e),
            }
    
    def get_interactive_agent(self, agent_type: str):
        """
        Get an instance of the specialized interactive agent.
        
        Args:
            agent_type: Either 'profile' or 'service'
        
        Returns:
            An instance of the specialized agent
        """
        if agent_type == "profile":
            return BuilderProfileCreationAgent()
        elif agent_type == "service":
            return BuilderServiceCreationAgent()
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
