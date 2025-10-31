"""
Builder Agent - LangGraph sub-router for builder-related tasks with cross-turn state.

Supports multi-task flows (e.g., create_profile -> create_service) and
preserves per-task state across turns by accepting and returning a
`builder_state`.
"""
import logging
import os
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import StateGraph, END

from .search_agent import BuilderSearchAgent
from .create_service_agent import BuilderServiceCreationAgent
from .create_profile_agent import BuilderProfileCreationAgent
from agents.listing.agent import AgentState  # Reuse state shape for single-step invokes
import json
import re

load_dotenv()


class BuilderRoutePlan(BaseModel):
    """Structured multi-task plan for builder requests."""
    tasks: List[Literal["search", "create_profile", "create_service"]] = Field(
        description="Ordered list of tasks inferred from the query.", default_factory=list
    )


def _classifier_llm():
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0,
    ).with_structured_output(BuilderRoutePlan)


def _classify_tasks_node(state: Dict[str, Any]):
    # If we already have a current task (continuation turn), skip reclassifying
    if state.get("current_task") or state.get("tasks"):
        # Ensure query is propagated forward
        return {"query": state.get("query", "")}
    query = state.get("query", "")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Classify the user's builder query into an ordered list of tasks. "
            "Only use: 'search', 'create_profile', 'create_service'. "
            "Example: 'I need to make builder profile then its service' -> "
            "['create_profile','create_service']. If none, return empty list."
        )),
        ("human", "{query}")
    ])
    chain = prompt | _classifier_llm()
    try:
        plan = chain.invoke({"query": query})
        tasks = list(plan.tasks or [])
    except Exception:
        tasks = []
    return {"tasks": tasks, "current_task": (tasks[0] if tasks else None), "query": query, "clerk_id": state.get("clerk_id")}


def _route_next(state: Dict[str, Any]):
    task = state.get("current_task")
    if not task:
        return "end"
    if task == "search":
        return "search_node"
    if task == "create_profile":
        return "create_profile_node"
    if task == "create_service":
        return "create_service_node"
    return "end"


def _advance(state: Dict[str, Any]):
    tasks: List[str] = state.get("tasks", [])
    if tasks:
        tasks.pop(0)
    state["tasks"] = tasks
    state["current_task"] = tasks[0] if tasks else None
    return state


def _parse_json_loose(text: str):
    try:
        return json.loads(text)
    except Exception:
        pass
    fenced = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text.strip())
    if fenced != text:
        try:
            return json.loads(fenced)
        except Exception:
            pass
    fixed = text.replace("{{", "{").replace("}}", "}")
    if fixed != text:
        try:
            return json.loads(fixed)
        except Exception:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            candidate2 = candidate.replace("{{", "{").replace("}}", "}")
            try:
                return json.loads(candidate2)
            except Exception:
                pass
    return None


def _profile_single_step(query: str, clerk_id: Optional[str], state: Dict[str, Any]) -> Dict[str, Any]:
    agent = BuilderProfileCreationAgent()
    # Persisted data/history
    profile_data: Dict[str, Any] = state.get("profile_data") or {
        "company_name": None,
        "specialization": None,
        "experience_years": None,
        "about": None,
        "city": None,
    }
    conversation_history: str = state.get("profile_history") or ""
    conversation_history += f"User: {query}\n"

    # Build the same prompt pattern the agent expects
    missing = ", ".join([
        f
        for f, v in [
            ("company_name", profile_data.get("company_name")),
            ("specialization", profile_data.get("specialization")),
            ("experience_years", profile_data.get("experience_years")),
            ("about", profile_data.get("about")),
            ("city", profile_data.get("city")),
        ]
        if (v is None or (isinstance(v, list) and not v))
    ])

    prompt_for_llm = f"""
            SYSTEM: {agent.system_prompt}

            Conversation History:
            {conversation_history}

            Current Data State (JSON):
            {json.dumps(profile_data)}

            Missing Fields Hint (ask in one question):
            {missing}

            User Context: The user's clerk_id is '{clerk_id}'. You must use this ID when calling the create_builder_profile_tool.
            
            NOW RESPOND - Check if all fields are complete, if YES call the tool, if NO return JSON.
            """

    initial_state = AgentState(
        messages=[{"role": "user", "content": prompt_for_llm.strip()}],
        query=conversation_history.strip(),
        data={"profile_data": profile_data},
        error=None,
        success=False,
        response="",
    )

    try:
        final_state = agent.app.invoke(initial_state, {"recursion_limit": 10})
        final_message = final_state["messages"][-1]
        content = final_message.content

        # Tool called => completion
        if getattr(final_message, "type", "") == "tool":
            try:
                tool_result = json.loads(content)
            except Exception:
                tool_result = {"success": True, "message": content}
            resp = tool_result.get("message", "Profile created successfully!")
            conversation_history += f"Agent: {resp}\n"
            return {
                "response": resp,
                "completed": True,
                "profile_data": profile_data,
                "profile_history": conversation_history,
                "error": tool_result.get("error"),
            }

        # JSON to continue
        parsed = None
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = _parse_json_loose(content)

        if isinstance(parsed, dict):
            resp = parsed.get("response", "Please provide the missing details.")
            updated = parsed.get("updated_data", profile_data)
            conversation_history += f"Agent: {resp}\n"
            return {
                "response": resp,
                "completed": parsed.get("status") == "completed",
                "profile_data": updated,
                "profile_history": conversation_history,
                "error": None,
            }

        # Fallback
        resp = content or "I didn't quite understand that. Could you please clarify?"
        conversation_history += f"Agent: {resp}\n"
        return {
            "response": resp,
            "completed": False,
            "profile_data": profile_data,
            "profile_history": conversation_history,
            "error": None,
        }
    except Exception as e:
        logging.getLogger(__name__).error(f"Profile single-step failed: {e}")
        return {
            "response": f"An unexpected error occurred: {str(e)}",
            "completed": False,
            "profile_data": profile_data,
            "profile_history": conversation_history,
            "error": str(e),
        }


def _service_single_step(query: str, clerk_id: Optional[str], state: Dict[str, Any]) -> Dict[str, Any]:
    agent = BuilderServiceCreationAgent()
    service_data: Dict[str, Any] = state.get("service_data") or {
        "title": None,
        "description": None,
        "category": None,
        "base_price": None,
        "price_unit": None,
        "estimated_duration": None,
        "service_features": None,
        "_opt_asked_duration": state.get("service_data", {}).get("_opt_asked_duration", False),
        "_opt_asked_features": state.get("service_data", {}).get("_opt_asked_features", False),
    }
    conversation_history: str = state.get("service_history") or ""
    conversation_history += f"User: {query}\n"

    prompt_for_llm = f"""
            SYSTEM: {agent.system_prompt}

            Conversation History:
            {conversation_history}

            Current Data State (JSON):
            {json.dumps(service_data)}

            User Context: The user's clerk_id is '{clerk_id}'. You must use this ID when calling the create_builder_service_tool.
            
            NOW RESPOND - Check if all required fields are complete, if YES call the tool, if NO return JSON.
            """

    initial_state = AgentState(
        messages=[{"role": "user", "content": prompt_for_llm.strip()}],
        query=conversation_history.strip(),
        data={"service_data": service_data},
        error=None,
        success=False,
        response="",
    )

    try:
        final_state = agent.app.invoke(initial_state, {"recursion_limit": 10})
        final_message = final_state["messages"][-1]
        content = final_message.content

        if getattr(final_message, "type", "") == "tool":
            tool_result = None
            if isinstance(content, dict):
                tool_result = content
            else:
                try:
                    tool_result = json.loads(content)
                except Exception:
                    tool_result = {"success": True, "message": content}
            resp = tool_result.get("message", "Service created successfully!")
            conversation_history += f"Agent: {resp}\n"
            return {
                "response": resp,
                "completed": True,
                "service_data": service_data,
                "service_history": conversation_history,
                "error": tool_result.get("error"),
            }

        parsed = None
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = _parse_json_loose(content)

        if isinstance(parsed, dict):
            resp = parsed.get("response", "Please provide the missing details.")
            updated = parsed.get("updated_data", service_data)
            conversation_history += f"Agent: {resp}\n"
            return {
                "response": resp,
                "completed": parsed.get("status") == "completed",
                "service_data": updated,
                "service_history": conversation_history,
                "error": None,
            }

        resp = content or "I didn't quite understand that. Could you please clarify?"
        conversation_history += f"Agent: {resp}\n"
        return {
            "response": resp,
            "completed": False,
            "service_data": service_data,
            "service_history": conversation_history,
            "error": None,
        }
    except Exception as e:
        logging.getLogger(__name__).error(f"Service single-step failed: {e}")
        return {
            "response": f"An unexpected error occurred: {str(e)}",
            "completed": False,
            "service_data": service_data,
            "service_history": conversation_history,
            "error": str(e),
        }


def _search_node(state: Dict[str, Any]):
    query = state.get("query", "")
    agent = BuilderSearchAgent()
    res = agent.process_query(query)
    msg = AIMessage(content=res.get("response", ""))
    messages: List[BaseMessage] = state.get("messages", [])
    messages.append(msg)
    # Always carry query forward
    new_state = _advance({**state, "messages": messages, "query": query, "clerk_id": state.get("clerk_id")})
    return new_state


def _create_profile_node(state: Dict[str, Any]):
    query = state.get("query", "")
    clerk_id = state.get("clerk_id")
    # Delegate full flow to the specific agent and wait for completion
    agent = BuilderProfileCreationAgent()
    res = agent.process_query(query, clerk_id=clerk_id)
    msg = AIMessage(content=res.get("response", ""))
    messages: List[BaseMessage] = state.get("messages", [])
    messages.append(msg)
    next_state = {**state, "messages": messages, "query": query, "clerk_id": state.get("clerk_id")}
    # Advance after specific agent completes its process
    return _advance(next_state)


def _create_service_node(state: Dict[str, Any]):
    query = state.get("query", "")
    clerk_id = state.get("clerk_id")
    # Delegate full flow to the specific agent and wait for completion
    agent = BuilderServiceCreationAgent()
    res = agent.process_query(query, clerk_id=clerk_id)
    msg = AIMessage(content=res.get("response", ""))
    messages: List[BaseMessage] = state.get("messages", [])
    messages.append(msg)
    next_state = {**state, "messages": messages, "query": query, "clerk_id": state.get("clerk_id")}
    # Advance after specific agent completes its process
    return _advance(next_state)


# Build the graph
workflow = StateGraph(dict)
workflow.add_node("classifier", _classify_tasks_node)
workflow.add_node("search_node", _search_node)
workflow.add_node("create_profile_node", _create_profile_node)
workflow.add_node("create_service_node", _create_service_node)

workflow.set_entry_point("classifier")
workflow.add_conditional_edges(
    "classifier",
    _route_next,
    {
        "search_node": "search_node",
        "create_profile_node": "create_profile_node",
        "create_service_node": "create_service_node",
        "end": END,
    },
)

for node in ["search_node", "create_profile_node", "create_service_node"]:
    workflow.add_conditional_edges(
        node,
        _route_next,
        {
            "search_node": "search_node",
            "create_profile_node": "create_profile_node",
            "create_service_node": "create_service_node",
            "end": END,
        },
    )

builder_agent_app = workflow.compile()


class BuilderAgent:
    """LangGraph-based builder sub-router."""

    def __init__(self):
        self.app = builder_agent_app
        self.name = "BuilderAgent"

    def process_query(self, query: str, clerk_id: Optional[str] = None, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not query or not query.strip():
            return {
                "success": False,
                "response": "Please provide a valid query.",
                "classification": "error",
                "error": "Empty query provided",
            }

        try:
            prior = state or {}
            init_state = {
                "query": query.strip(),
                "clerk_id": clerk_id,
                "tasks": prior.get("tasks", []),
                "current_task": prior.get("current_task"),
                "messages": prior.get("messages", []),
                # Persisted subtask state
                "profile_data": prior.get("profile_data"),
                "profile_history": prior.get("profile_history"),
                "service_data": prior.get("service_data"),
                "service_history": prior.get("service_history"),
            }
            final_state = self.app.invoke(init_state)
            messages: List[BaseMessage] = final_state.get("messages", [])
            response_content = messages[-1].content if messages else (
                "I can help with builders: search, create profile, or create service."
            )
            classification = (
                ",".join(final_state.get("tasks", [])) if final_state.get("tasks") else "builder_general"
            )
            return {
                "success": True,
                "response": response_content,
                "classification": classification,
                "error": None,
                # Return state so caller can continue multi-turn
                "state": {
                    "tasks": final_state.get("tasks", []),
                    "current_task": final_state.get("current_task"),
                    "messages": [m for m in messages],
                    "profile_data": final_state.get("profile_data"),
                    "profile_history": final_state.get("profile_history"),
                    "service_data": final_state.get("service_data"),
                    "service_history": final_state.get("service_history"),
                },
            }
        except Exception as e:
            logging.getLogger(__name__).error(f"BuilderAgent failed: {e}")
            return {
                "success": False,
                "response": f"An error occurred while processing your builder request: {str(e)}",
                "classification": "error",
                "error": str(e),
            }
