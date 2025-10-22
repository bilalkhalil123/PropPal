"""
Base Agent class for PropPal AI agents using LangGraph.

Essential LangGraph functionality for building AI agents.
"""
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, TypedDict
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for LangGraph agents with tool selection."""
    query: str
    response: str
    data: Dict[str, Any]
    error: Optional[str]
    success: bool
    selected_tool: Optional[str]
    tool_args: Dict[str, Any]


class BaseAgent:
    """Base class for PropPal AI agents using LangGraph."""
    
    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: Optional[List] = None,
        model_name: str = "phi3:mini"
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools or []
        
        # Initialize LLM
        self.llm = ChatOllama(
            model=model_name,
            base_url="http://localhost:11434",
            temperature=0.7
        )
        
        # Create the LangGraph workflow
        self.graph = self._create_graph()
        self.app = self.graph.compile()
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow with tool selection."""
        workflow = StateGraph(AgentState)
        
        # Add workflow nodes
        workflow.add_node("classify", self._classify_intent)
        workflow.add_node("execute", self._execute_tool)
        workflow.add_node("respond", self._generate_response)
        
        # Add edges
        workflow.add_edge("classify", "execute")
        workflow.add_edge("execute", "respond")
        workflow.add_edge("respond", END)
        
        # Set entry point
        workflow.set_entry_point("classify")
        
        return workflow
    
    def _classify_intent(self, state: AgentState) -> AgentState:
        """Classify user intent and select appropriate tool."""
        query = state.get("query", "").strip()
        
        # Basic validation
        if not query:
            state["error"] = "Empty query provided"
            state["success"] = False
            return state
        
        # If no tools available, skip tool selection
        if not self.tools:
            state["selected_tool"] = None
            state["tool_args"] = {}
            return state
        
        try:
            # Use LLM to classify intent and select tool
            tool_catalog = self._build_tool_catalog()
            prompt = self._create_classification_prompt(query, tool_catalog)
            
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, "content") else str(response)
            
            # Parse LLM response
            classification = self._parse_classification(response_text)
            
            if classification:
                state["selected_tool"] = classification.get("tool_name")
                state["tool_args"] = classification.get("tool_args", {})
            else:
                # Fallback: use first tool
                state["selected_tool"] = self.tools[0].name if hasattr(self.tools[0], 'name') else "tool_0"
                state["tool_args"] = {"query": query}
                
        except Exception as e:
            logger.warning(f"Classification failed: {e}, using fallback")
            state["selected_tool"] = self.tools[0].name if hasattr(self.tools[0], 'name') else "tool_0"
            state["tool_args"] = {"query": query}
        
        return state
    
    def _execute_tool(self, state: AgentState) -> AgentState:
        """Execute the selected tool."""
        selected_tool = state.get("selected_tool")
        tool_args = state.get("tool_args", {})
        
        if not selected_tool or not self.tools:
            # No tool selected, use LLM directly
            query = state.get("query", "")
            response = self.llm.invoke(f"{self.system_prompt}\n\nQuery: {query}")
            state["response"] = response.content if hasattr(response, "content") else str(response)
            state["data"] = {}
            state["success"] = True
            return state
        
        try:
            # Find and execute the selected tool
            tool = self._find_tool(selected_tool)
            if tool:
                result = tool.invoke(tool_args)
                state["data"] = result
                state["success"] = True
            else:
                state["error"] = f"Tool '{selected_tool}' not found"
                state["success"] = False
                
        except Exception as e:
            state["error"] = f"Tool execution failed: {str(e)}"
            state["success"] = False
        
        return state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate final response."""
        if state.get("error"):
            state["response"] = f"I apologize, but I encountered an error: {state['error']}"
        elif state.get("success") and state.get("data"):
            # Generate response based on tool results
            state["response"] = self._format_tool_response(state)
        else:
            # Use existing response or generate one
            if not state.get("response"):
                query = state.get("query", "")
                response = self.llm.invoke(f"{self.system_prompt}\n\nQuery: {query}")
                state["response"] = response.content if hasattr(response, "content") else str(response)
        
        return state
    
    # ========== Helper Methods ==========
    
    def _build_tool_catalog(self) -> List[Dict[str, str]]:
        """Build a catalog of available tools for the LLM."""
        catalog = []
        for i, tool in enumerate(self.tools):
            try:
                tool_name = getattr(tool, "name", f"tool_{i}")
                tool_desc = getattr(tool, "description", "") or getattr(tool, "__doc__", "") or "No description"
                catalog.append({
                    "name": tool_name,
                    "description": tool_desc.strip()
                })
            except Exception as e:
                logger.warning(f"Could not extract tool info: {e}")
                catalog.append({
                    "name": f"tool_{i}",
                    "description": "Tool description unavailable"
                })
        return catalog
    
    def _create_classification_prompt(self, query: str, tool_catalog: List[Dict[str, str]]) -> str:
        """Create prompt for tool classification."""
        tools_str = "\n".join([f"- {tool['name']}: {tool['description']}" for tool in tool_catalog])
        
        return f"""You are {self.name}, an AI assistant.

{self.system_prompt}

Available tools:
{tools_str}

User query: "{query}"

Analyze the query and select the most appropriate tool. Return ONLY valid JSON:
{{
  "tool_name": "selected_tool_name",
  "tool_args": {{"param1": "value1", "param2": "value2"}}
}}

If no tool is suitable, return:
{{
  "tool_name": null,
  "tool_args": {{}}
}}

Return ONLY the JSON, nothing else."""
    
    def _parse_classification(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse LLM classification response."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            data = json.loads(response_text)
            
            if isinstance(data, dict) and "tool_name" in data:
                return data
                
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Failed to parse classification: {e}")
        
        return None
    
    def _find_tool(self, tool_name: str) -> Optional[Any]:
        """Find a tool by name."""
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                return tool
        return None
    
    def _format_tool_response(self, state: AgentState) -> str:
        """Format tool response into human-readable text."""
        data = state.get("data", {})
        
        # Default formatting - can be overridden by subclasses
        if data.get("success"):
            count = data.get("count", 0)
            if count > 0:
                return f"Found {count} results matching your query."
            else:
                return "No results found for your query."
        else:
            return "I found some information, but there was an issue processing it."
    
    # ========== Public API ==========
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query using the LangGraph workflow."""
        # Create initial state
        initial_state = AgentState(
            query=query,
            response="",
            data={},
            error=None,
            success=False,
            selected_tool=None,
            tool_args={}
        )
        
        # Run the workflow
        try:
            final_state = self.app.invoke(initial_state)
            return {
                "success": final_state["success"],
                "response": final_state.get("response", ""),
                "data": final_state.get("data", {}),
                "error": final_state.get("error")
            }
        except Exception as e:
            return {
                "success": False,
                "response": f"Error: {str(e)}",
                "data": {},
                "error": str(e)
            }
