"""
Router Agent - Orchestrator for multiple specialized agents.
Routes user queries to the appropriate specialized agent.
"""

import operator
import os
from typing import TypedDict, Annotated, List, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from dotenv import load_dotenv
# Load .env file
load_dotenv()

# Import the ListingAgent
from agents.listing.agent import ListingAgent
from .builder.agent import BuilderAgent

# --- Define the Router's State ---
# This is the state for the *main orchestrator* graph.
class RouterState(TypedDict):
    # The user's original query
    query: str

    # User identifier for creation tasks
    clerk_id: Optional[str]
    
    # The classification result from the router
    classification: str
    
    # The list of messages (conversation history)
    # operator.add allows us to append messages to this list
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Properties and builders from agent responses
    properties: List[dict]
    builders: List[dict]

# --- LLM and Router Definition ---

# Initialize the LLM for the router
# This LLM's only job is to classify the query, so it's very fast.
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)

# Define the structured output for our router
class RouteQuery(BaseModel):
    """Classify the user's query to route it to the correct agent."""
    destination: str = Field(
        description="The destination node. Must be one of 'listing_agent', 'builder_agent', or 'general_chat'."
    )

# Bind the structured output to the LLM
structured_llm = llm.with_structured_output(RouteQuery)

# --- Agent Factory Functions ---
# We create fresh instances of agents to avoid state issues
def get_listing_agent():
    """Get a fresh instance of ListingAgent."""
    return ListingAgent()

def get_builder_agent():
    """Get a fresh instance of BuilderAgent."""
    return BuilderAgent()

# In the future, you could add:
# def get_financial_agent():
#     return FinancialAgent()
# def get_support_agent():
#     return SupportAgent()


# --- Main Router Graph Nodes ---

def classify_intent_node(state: RouterState):
    """
    This is the first node that runs. It classifies the user's query.
    """
    print("--- [Main Graph] Classifying Intent ---")
    query = state['query']
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert router for PropPal, a real estate platform. Your job is to classify the user's query. "
            "Respond with 'listing_agent' if they are asking about real estate, "
            "property, listings, houses, apartments, buying, selling, renting, "
            "property search, property details, or property prices. "
            "Respond with 'builder_agent' if the query is about builders, contractors, construction, renovation, creating a builder profile, or creating a builder service. "
            "For anything else (like 'hello', 'how are you', 'who are you?', "
            "general questions, platform help, etc.), respond with 'general_chat'."
            # "In the future, you might also route to 'financial_agent' "
            # "for mortgage questions."
        )),
        ("human", "{query}")
    ])
    
    # Create the classification chain
    chain = prompt | structured_llm
    
    # Invoke the chain and get the structured result
    result = chain.invoke({"query": query})
    
    print(f"--- [Main Graph] Classification: {result.destination} ---")
    # Update the state with the classification
    return {"classification": result.destination}

def general_chat_node(state: RouterState):
    """
    This node handles all non-property-related queries (e.g., "Hello").
    """
    print("--- [Main Graph] Executing General Chat ---")
    query = state['query']
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a helpful assistant for PropPal, a real estate platform. "
            "You can help users with general questions about the platform, "
            "account issues, or general conversation. You do *not* search for properties. "
            "If users ask about property-related topics, politely redirect them to "
            "ask about specific property searches."
        )),
        ("human", "{query}")
    ])
    
    # Use the same LLM or a different one
    chain = prompt | llm
    result = chain.invoke({"query": query})
    
    return {"messages": [result]}

def listing_agent_node(state: RouterState):
    """
    This node acts as a "client" to your ListingAgent class.
    It calls the agent's public API and formats the response for the graph.
    """
    print("--- [Main Graph] Routing to Listing Agent ---")
    query = state['query']
    
    # Create a fresh instance of ListingAgent to avoid state issues
    listing_agent = get_listing_agent()
    
    # Call the .process_query() method from your imported agent
    # This is the key: we are calling the compiled agent's public method.
    result = listing_agent.process_query(query)
    
    # The agent's public API returns a dict.
    # We'll use the 'response' field for the chat history.
    response_message = result.get("response", "An error occurred in the listing agent.")
    properties = result.get("properties", [])
    
    if not result.get("success"):
        print(f"--- [Main Graph] Listing Agent Error: {result.get('error')}")
        # Even if it fails, we pass the error message back to the user
        
    return {
        "messages": [AIMessage(content=response_message)],
        "properties": properties
    }

def builder_agent_node(state: RouterState):
    """
    This node acts as a "client" to the BuilderAgent class.
    It calls the agent's public API and formats the response for the graph.
    """
    print("--- [Main Graph] Routing to Builder Agent ---")
    query = state['query']
    clerk_id = state.get('clerk_id')

    # Create a fresh instance of BuilderAgent
    builder_agent = get_builder_agent()

    # Call the .process_query() method, passing along clerk_id
    result = builder_agent.process_query(query, clerk_id=clerk_id)

    response_message = result.get("response", "An error occurred in the builder agent.")
    builders = result.get("builders", result.get("results", []))
    if not result.get("success"):
        print(f"--- [Main Graph] Builder Agent Error: {result.get('error')}")

    return {
        "messages": [AIMessage(content=response_message)],
        "builders": builders
    }
# --- Conditional Routing Function ---

def route_after_classification(state: RouterState):
    """
    This function reads the 'classification' from the state
    and returns the name of the *next* node to run.
    """
    classification = state.get("classification")
    
    if classification == "listing_agent":
        return "listing_agent_node"
    elif classification == "builder_agent":
        return "builder_agent_node"
    # elif classification == "financial_agent":
    #     return "financial_agent_node" # For the future
    else:
        # Route to the general chat node
        return "general_chat_node"

# --- Build the Main Router Graph ---

workflow = StateGraph(RouterState)

# 1. Add the nodes
workflow.add_node("classifier", classify_intent_node)
workflow.add_node("general_chat_node", general_chat_node)
workflow.add_node("listing_agent_node", listing_agent_node)
workflow.add_node("builder_agent_node", builder_agent_node)
# In the future, you'd add more agent nodes here

# 2. Define the entry point
workflow.set_entry_point("classifier")

# 3. Add the conditional router edge
workflow.add_conditional_edges(
    "classifier", # Start node
    route_after_classification, # Function that decides the route
    {
        # Mapping: 'classification' -> 'node_name'
        "listing_agent_node": "listing_agent_node",
        "general_chat_node": "general_chat_node",
        "builder_agent_node": "builder_agent_node",
        # "financial_agent_node": "financial_agent_node" # For the future
    }
)

# 4. Define the end points
#    After any agent node runs, the graph ends.
workflow.add_edge("general_chat_node", END)
workflow.add_edge("listing_agent_node", END)
workflow.add_edge("builder_agent_node", END)
# workflow.add_edge("financial_agent_node", END) # For the future

# 5. Compile the main graph
router_agent_app = workflow.compile()


# --- Public API for the Router Agent ---

class RouterAgent:
    """
    Public interface for the Router Agent.
    This provides a clean API for external use.
    """
    
    def __init__(self):
        self.app = router_agent_app
        self.name = "RouterAgent"
    
    def process_query(self, query: str, clerk_id: Optional[str] = None) -> dict:
        """
        Process a user query through the router agent.
        
        Args:
            query: The user's query string
            clerk_id: The user's Clerk ID (optional).
            
        Returns:
            dict: Response containing success, response, and metadata
        """
        if not query or not query.strip():
            return {
                "success": False,
                "response": "Please provide a valid query.",
                "classification": "error",
                "properties": [],
                "builders": [],
                "error": "Empty query provided"
            }
        
        try:
            # Create initial state
            initial_state = RouterState(
                query=query.strip(),
                clerk_id=clerk_id,
                classification="",
                messages=[],
                properties=[],
                builders=[]
            )
            
            # Run the router workflow
            final_state = self.app.invoke(initial_state)
            
            # Extract the final response from the last message
            if final_state.get("messages"):
                final_message = final_state["messages"][-1]
                response_content = final_message.content if hasattr(final_message, 'content') else str(final_message)
            else:
                response_content = "No response generated"
            
            return {
                "success": True,
                "response": response_content,
                "classification": final_state.get("classification", "unknown"),
                "properties": final_state.get("properties", []),
                "builders": final_state.get("builders", []),
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": f"An error occurred while processing your query: {str(e)}",
                "classification": "error",
                "properties": [],
                "builders": [],
                "error": str(e)
            }
