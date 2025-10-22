# PropPal Agents Usage Guide

This guide shows how to run the simplified PropPal AI agents using LangGraph.

## Prerequisites

1. **Ollama installed and running**:
   ```bash
   # Install Ollama (if not already installed)
   # Download from: https://ollama.ai/
   
   # Pull the required model
   ollama pull phi3:mini
   
   # Start Ollama server
   ollama serve
   ```

2. **Backend API running**:
   ```bash
   cd apps/backend
   python -m uvicorn services.main:app --reload --port 8000
   ```

## Quick Start

### 1. Basic Agent Usage

```python
from agents.listing.agent import ListingAgent

# Create agent
agent = ListingAgent()

# Process a query
result = agent.process_query("Find apartments in Islamabad")

print(f"Success: {result['success']}")
print(f"Response: {result['response']}")
print(f"Properties found: {result['count']}")
```

### 2. Using Base Agent

```python
from agents.base.agent import BaseAgent

# Create a simple agent
agent = BaseAgent(
    name="SimpleAgent",
    system_prompt="You are a helpful assistant."
)

# Process query
result = agent.process_query("Hello, how are you?")
print(result)
```

### 3. Running from API

The agents are integrated with the FastAPI backend. You can use them via HTTP:

```bash
# Search for properties
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Find houses in Karachi"}'
```

## Agent Architecture

### BaseAgent (LangGraph Core)
- **Purpose**: Generic foundation for all agents using LangGraph
- **Key Features**:
  - **Tool Classification**: LLM automatically selects appropriate tool
  - **Multi-tool Support**: Handle multiple tools per agent
  - **LangGraph Workflow**: `classify` → `execute` → `respond` → `END`
  - **State Management**: Track query, selected tool, tool args, and results
  - **Error Handling**: Graceful fallbacks and error management

### ListingAgent (Property Search)
- **Purpose**: Search for properties
- **Tools**: `property_search_tool`
- **Usage**: Natural language property queries
- **Custom Response**: Property-specific response formatting

## File Structure

```
agents/
├── base/
│   └── agent.py          # BaseAgent class
├── listing/
│   ├── agent.py          # ListingAgent class
│   └── tools/
│       └── property_search.py  # Property search tool
└── USAGE_GUIDE.md        # This file
```

## Key Components

### AgentState (Tool-Aware)
```python
class AgentState(TypedDict):
    query: str
    response: str
    data: Dict[str, Any]
    error: Optional[str]
    success: bool
    selected_tool: Optional[str]
    tool_args: Dict[str, Any]
```

### LangGraph Workflow
```python
workflow = StateGraph(AgentState)
workflow.add_node("classify", self._classify_intent)
workflow.add_node("execute", self._execute_tool)
workflow.add_node("respond", self._generate_response)
workflow.add_edge("classify", "execute")
workflow.add_edge("execute", "respond")
workflow.add_edge("respond", END)
workflow.set_entry_point("classify")
```

## Error Handling

The agents include basic error handling:
- Empty query validation
- API call failures
- Tool execution errors
- Graceful fallbacks

## Customization

### Adding New Agents

1. Create agent file: `agents/{name}/agent.py`
2. Inherit from `BaseAgent`
3. Override `_format_tool_response()` for custom responses
4. Add tools to `tools/` directory
5. The LLM will automatically classify and select tools

### Adding New Tools

1. Create tool file: `agents/{name}/tools/{tool_name}.py`
2. Use `@tool` decorator from `langchain_core.tools`
3. Add `name` and `description` attributes for better classification
4. Import and use in agent

### Example Multi-Tool Agent

```python
from agents.base.agent import BaseAgent
from langchain_core.tools import tool

@tool
def tool_one(param: str) -> Dict[str, Any]:
    """Description of what tool_one does."""
    return {"result": "data"}

@tool  
def tool_two(param: str) -> Dict[str, Any]:
    """Description of what tool_two does."""
    return {"result": "data"}

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="MyAgent",
            system_prompt="You are a helpful assistant...",
            tools=[tool_one, tool_two]
        )
    
    def _format_tool_response(self, state: AgentState) -> str:
        # Custom response formatting based on selected tool
        return "Custom response"
```

## Troubleshooting

### Common Issues

1. **Ollama not running**:
   ```bash
   ollama serve
   ```

2. **Model not found**:
   ```bash
   ollama pull phi3:mini
   ```

3. **API not responding**:
   - Check if backend is running on port 8000
   - Verify search API endpoint is working

4. **Import errors**:
   - Ensure you're running from the backend directory
   - Check Python path includes the agents directory

### Debug Mode

Enable logging to see agent processing:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Performance

- **Simple workflow**: Single node processing
- **Minimal overhead**: Removed complex state management
- **Fast execution**: Direct tool calls
- **Memory efficient**: Simplified state structure

## Next Steps

1. **Test the agents** with sample queries
2. **Add more tools** as needed
3. **Create specialized agents** for different use cases
4. **Integrate with your application** via the API endpoints
