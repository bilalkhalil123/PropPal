"""
LangGraph booking agent: Groq + tools for scheduling property visits.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from agents.booking.tools import build_booking_tools

load_dotenv()
logger = logging.getLogger(__name__)


class BookingAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    error: Optional[str]
    success: bool


def _history_to_messages(
    history: List[Dict[str, Any]], new_user_text: str
) -> List[BaseMessage]:
    out: List[BaseMessage] = []
    for turn in history:
        role = (turn.get("role") or "").lower()
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
    out.append(HumanMessage(content=new_user_text.strip()))
    return out


def _extract_last_visit_from_messages(messages: List[BaseMessage]) -> Optional[Dict[str, Any]]:
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue
        raw = msg.content
        if not isinstance(raw, str):
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("success") and data.get("visit"):
            v = data["visit"]
            if isinstance(v, dict):
                return _normalize_visit(v)
    return None


def _normalize_visit(v: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(v)
    ct = out.get("confirmed_time")
    if hasattr(ct, "isoformat"):
        out["confirmed_time"] = ct.isoformat()
    return out


class BookingAgent:
    """Per-request agent: build with tools from build_booking_tools(...)."""

    def __init__(
        self,
        system_prompt: str,
        tools: List,
        model_name: str = "llama-3.1-8b-instant",
    ):
        self.system_prompt = system_prompt
        self.tools = tools
        self.llm = ChatGroq(
            model=model_name,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1,
            max_tokens=512,
        )
        self.llm_with_tools = self.llm.bind_tools(tools)
        self.tool_executor = ToolNode(tools)
        self.graph = self._create_graph()
        self.app = self.graph.compile()

    def _create_graph(self) -> StateGraph:
        workflow = StateGraph(BookingAgentState)
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("execute_tools", self._tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {"continue": "execute_tools", "end": END},
        )
        workflow.add_edge("execute_tools", "agent")
        return workflow

    def _should_continue(self, state: BookingAgentState) -> str:
        if not state["messages"]:
            return "end"
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "continue"
        return "end"

    def _agent_node(self, state: BookingAgentState) -> Dict[str, Any]:
        messages = [SystemMessage(content=self.system_prompt)] + state["messages"]
        try:
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response], "success": True}
        except Exception as e:
            logger.error("Booking agent node failed: %s", e)
            return {
                "messages": [
                    AIMessage(
                        content="Sorry, I could not process that. Please try again."
                    )
                ],
                "error": str(e),
                "success": False,
            }

    def _tool_node(self, state: BookingAgentState) -> Dict[str, Any]:
        try:
            tool_result = self.tool_executor.invoke(state)
            if isinstance(tool_result, dict) and "messages" in tool_result:
                tool_messages = tool_result["messages"]
            else:
                tool_messages = tool_result
            # Keep full JSON tool payloads so we can extract visit_object after the run.
            return {"messages": list(tool_messages), "success": True}
        except Exception as e:
            logger.error("Booking tool node failed: %s", e)
            return {
                "messages": [
                    ToolMessage(
                        content=f"Tool error: {e}",
                        tool_call_id="error",
                    )
                ],
                "error": str(e),
                "success": False,
            }

    def process(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        history = conversation_history or []
        msgs = _history_to_messages(history, user_message)
        initial: BookingAgentState = {
            "messages": msgs,
            "error": None,
            "success": True,
        }
        try:
            final = self.app.invoke(initial, {"recursion_limit": 10})
        except Exception as e:
            logger.error("Booking graph failed: %s", e)
            return {
                "success": False,
                "agent_response": f"Something went wrong: {e}",
                "last_visit": None,
                "error": str(e),
            }

        out_msgs = final.get("messages") or []
        agent_response = ""
        for m in reversed(out_msgs):
            if isinstance(m, AIMessage) and m.content:
                agent_response = str(m.content)
                break

        last_visit = _extract_last_visit_from_messages(out_msgs)

        return {
            "success": final.get("success", True),
            "agent_response": agent_response or "No response.",
            "last_visit": last_visit,
            "error": final.get("error"),
        }


def build_booking_system_prompt(
    property_title: str,
    property_id: str,
    seller_id: str,
    city: str,
    area: str,
    calendar_context: str = "",
    existing_visit_context: str = "",
) -> str:
    loc = f"{area}, {city}".strip(", ")
    cal = (calendar_context or "").strip()
    ex = (existing_visit_context or "").strip()
    extra = ""
    if cal:
        extra += f"\n{cal}\n"
    if ex:
        extra += f"\n{ex}\n"

    return f"""You are PropPal's visit-scheduling assistant for a single property listing.

FIXED CONTEXT (do not ask the user for these IDs):
- property_id: {property_id}
- seller_id: {seller_id}
- Property: {property_title}
- Location: {loc}
{extra}
RULES:
- Be concise and conversational. Prefer short replies.

SLOTS FIRST (mandatory):
- If the user only names a weekday, date, or vague window (e.g. "Tuesday", "next week", "morning") with NO specific clock time yet: call get_available_slots using dates from the CALENDAR section above, then reply with ONLY the numbered available times and ask which one they want. Do NOT call create_visit_booking in that same turn.
- You may ONLY call create_visit_booking after the user has clearly picked a specific time that matches one of the slots returned by get_available_slots (e.g. "4pm", "5:00 PM", "option 3", "the 9am slot"). If their time does not match any returned slot, say so and show options again—never invent a time.

NO EARLY BOOKING OR CONFIRMATION:
- Do not say you created or booked a visit unless you have just called create_visit_booking in this conversation after their explicit time choice.
- Never call confirm_visit unless the user explicitly agrees to confirm (e.g. "yes", "confirm", "go ahead", "please confirm", "that works—confirm it"). Do not call confirm_visit in the same assistant turn as create_visit_booking. Do not treat "would you like to confirm?" as them saying yes—they must answer affirmatively first.

PENDING VISIT CHANGES:
- If EXISTING VISIT ON THIS LISTING is set above, or get_user_visits shows pending/confirmed for this property, do NOT create_visit_booking—use reschedule_visit (after get_available_slots) or cancel_visit. Ask if they want to change time when relevant.

OTHER:
- Only offer times from get_available_slots; describe them in plain English (no raw ISO in replies).
- For create_visit_booking / reschedule_visit, use the exact ISO from the tool's `slots` array matching the user's choice.
- Notes about the tour (e.g. terrace): append_visit_notes with visit_id from get_user_visits or the last booking.

TOOLS: get_property_context (optional), get_available_slots, create_visit_booking, confirm_visit, cancel_visit, reschedule_visit, get_user_visits, append_visit_notes.
"""
