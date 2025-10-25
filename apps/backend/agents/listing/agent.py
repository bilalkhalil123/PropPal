"""
Simplified Listing Agent for property search using LangGraph.
"""

import logging
import os
import json
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from .tools.property_search import property_search_tool

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """
    Updated state for a cyclical agent.
    'messages' is the core of the loop.
    Other keys are kept to match the process_query API.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    data: Dict[str, Any]
    error: Optional[str]
    success: bool
    response: str  # Will be populated at the end


class ListingAgent:
    """
    A simplified, cyclical agent for property search using LangGraph.
    """
    
    def __init__(self, model_name: str = "llama-3.1-8b-instant"):
        
        # System prompt defines the agent's role and tool use
        self.system_prompt = """You are a Property Search Agent for PropPal.

Your job is to help users find properties by using the property_search_tool.

CRITICAL INSTRUCTIONS:
- When a user asks about properties, you MUST immediately call the property_search_tool with their exact query
- Do NOT ask follow-up questions or explain what you're doing
- Do NOT generate text like <function=property_search_tool> - use the actual tool call
- Just call the tool and then present the results

For general questions (like "hello", "how are you"), answer naturally without using tools.

After using the property_search_tool, present the results clearly to the user.
If no properties are found, inform them politely and suggest they try different search terms.
"""
        
        self.tools = [property_search_tool]
        
        # Helper to execute tools
        self.tool_executor = ToolNode(self.tools)
        
        # Initialize LLM and bind tools
        self.llm = ChatGroq(
            model=model_name,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1  # Lower temperature for more consistent tool calling
        )
        # Bind tools to the LLM for automatic tool-call formatting
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Create the LangGraph workflow
        self.graph = self._create_graph()
        self.app = self.graph.compile()

    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Add workflow nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("execute_tools", self._tool_node)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "execute_tools",  # If tool call, run tools
                "end": END                   # If no tool call, end
            }
        )
        
        # Add edge from tool execution back to agent
        workflow.add_edge("execute_tools", "agent")
        
        return workflow

    # ========== Graph Nodes ==========

    def _should_continue(self, state: AgentState) -> str:
        """Conditional router: checks for tool calls."""
        if not state["messages"]:
            return "end"
        last_message = state["messages"][-1]
        # If the last message has tool calls, route to tool executor
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "continue"
        # Otherwise, end the conversation
        return "end"

    def _agent_node(self, state: AgentState) -> Dict[str, Any]:
        """
        The "brain" of the agent. Invokes the LLM with the current state.
        """
        messages = [SystemMessage(content=self.system_prompt)] + state["messages"]
        
        # Invoke the LLM with bound tools
        try:
            response = self.llm_with_tools.invoke(messages)
            
            # Debug: Log the response to see what's happening
            logger.info(f"Agent response type: {type(response)}")
            if hasattr(response, 'tool_calls'):
                logger.info(f"Tool calls: {response.tool_calls}")
            else:
                logger.info(f"No tool calls in response")
                logger.info(f"Response content: {response.content[:200]}...")
            
            # 'add_messages' will append this to the state's 'messages' list
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"Agent node failed: {e}")
            return {"error": str(e), "success": False}

    def _tool_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Executes tools, parses results, and updates the state.
        """
        try:
            logger.info(f"Tool node called with state: {state}")
            
            # Call the pre-built ToolNode to get ToolMessages
            tool_result = self.tool_executor.invoke(state)
            logger.info(f"Tool result type: {type(tool_result)}")
            logger.info(f"Tool result: {tool_result}")
            
            # Extract messages from the result
            if isinstance(tool_result, dict) and "messages" in tool_result:
                tool_messages = tool_result["messages"]
            else:
                tool_messages = tool_result

            logger.info(f"Tool messages: {tool_messages}")

            # We assume only one tool call for property search
            data_result = {}
            success = False
            
            for msg in tool_messages:
                if isinstance(msg, ToolMessage):
                    logger.info(f"Processing ToolMessage: {msg.content}")
                    try:
                        # Parse the tool's JSON output
                        tool_data = json.loads(msg.content)
                        logger.info(f"Parsed tool data: {tool_data}")
                        if tool_data.get("success"):
                            data_result = tool_data
                            success = True
                            break  # Found our data
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        continue  # Not valid JSON, skip

            logger.info(f"Final data_result: {data_result}")
            logger.info(f"Final success: {success}")

            return {
                "messages": tool_messages,
                "data": data_result,  # <-- Update the state's 'data' field
                "success": success    # <-- Update the state's 'success' field
            }
        
        except Exception as e:
            logger.error(f"Tool node failed: {e}")
            error_message = ToolMessage(content=f"Tool execution failed: {e}", tool_call_id="error_000")
            return {"messages": [error_message], "error": str(e), "success": False}

    # ========== Public API ==========
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a property search query using the LangGraph workflow."""
        
        # Validate input
        if not query or not query.strip():
            return {
                "success": False,
                "response": "Please provide a valid search query.",
                "properties": [],
                "count": 0,
                "error": "Empty query provided"
            }
        
        # Create initial state
        initial_state = AgentState(
            messages=[HumanMessage(content=query.strip())],
            query=query.strip(),
            data={},
            error=None,
            success=False,
            response=""
        )
        
        # Run the workflow
        try:
            final_state = self.app.invoke(initial_state, {"recursion_limit": 5})
            
            # The final response is the agent's last message
            final_response = final_state["messages"][-1].content
            
            # --- THIS IS THE CLEAN PART ---
            # Data is now directly available in the final state!
            data = final_state.get("data", {})
            properties = data.get("results", [])
            count = data.get("count", 0)
            
            return {
                "success": final_state.get("success", True),  # 'success' was set by our tool node
                "response": final_response,
                "properties": properties,
                "count": count,
                "error": final_state.get("error")
            }
        except Exception as e:
            logger.error(f"Graph invocation failed: {e}")
            return {
                "success": False,
                "response": f"An unexpected error occurred: {str(e)}",
                "properties": [],
                "count": 0,
                "error": str(e)
            }
