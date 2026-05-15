"""
Lab 6 — Secured LangGraph with Guardrail Nodes for SCDRA.

Wraps the single-agent ReAct graph with:
  - A guardrail_node that runs BEFORE the agent_node
  - An alert_node that returns a standardized refusal
  - Output sanitization on every agent response

If input is classified as UNSAFE, the graph routes directly to the
alert_node — the agent LLM is never invoked.
"""

import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from tools import ALL_TOOLS
from graph import SYSTEM_PROMPT
from guardrails_config import (
    run_deterministic_guardrail,
    run_llm_judge_guardrail,
    sanitize_output,
    SafetyVerdict,
)

load_dotenv()


# ---------------------------------------------------------------------------
# State (extended with guardrail fields)
# ---------------------------------------------------------------------------
class SecuredState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    guardrail_verdict: str
    guardrail_reason: str


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)
llm_with_tools = llm.bind_tools(ALL_TOOLS)


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
def guardrail_node(state: SecuredState) -> dict:
    """Run input through both guardrail layers before the agent sees it."""
    user_input = ""
    for msg in reversed(state["messages"]):
        if hasattr(msg, "content") and hasattr(msg, "type") and msg.type == "human":
            user_input = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    if not user_input:
        return {"guardrail_verdict": "SAFE", "guardrail_reason": "No user input found."}

    # Layer 1: Deterministic
    det_result = run_deterministic_guardrail(user_input)
    if det_result.verdict == SafetyVerdict.UNSAFE:
        return {
            "guardrail_verdict": "UNSAFE",
            "guardrail_reason": f"[Deterministic] {det_result.reason} (Rule: {det_result.matched_rule})",
        }

    # Layer 2: LLM-as-a-Judge
    try:
        llm_result = run_llm_judge_guardrail(user_input)
        if llm_result.verdict == SafetyVerdict.UNSAFE:
            return {
                "guardrail_verdict": "UNSAFE",
                "guardrail_reason": f"[LLM Judge] {llm_result.reason}",
            }
    except Exception:
        pass

    return {"guardrail_verdict": "SAFE", "guardrail_reason": "Input passed all guardrails."}


def agent_node(state: SecuredState) -> dict:
    """Invoke the LLM with the current messages and bound tools."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
    response = llm_with_tools.invoke(messages)

    # Apply output sanitization
    if isinstance(response.content, str):
        response = AIMessage(
            content=sanitize_output(response.content),
            tool_calls=response.tool_calls if hasattr(response, "tool_calls") else [],
        )

    return {"messages": [response]}


def alert_node(state: SecuredState) -> dict:
    """Return a standardized refusal when input is classified as UNSAFE."""
    refusal = (
        "I've detected a prompt manipulation attempt. I must stay on topic and "
        "follow my designated instructions. I am the Supply Chain Disruption "
        "Response Agent (SCDRA) and can only assist with:\n"
        "- Analyzing supply chain disruptions and their impact\n"
        "- Querying inventory levels and purchase orders\n"
        "- Searching for alternative suppliers and comparing pricing\n"
        "- Calculating financial exposure and risk scores\n"
        "- Looking up standard operating procedures\n"
        "- Drafting response plans for human approval\n\n"
        "How can I help with your supply chain needs?"
    )
    return {"messages": [AIMessage(content=refusal)]}


tool_node = ToolNode(ALL_TOOLS)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
def route_after_guardrail(state: SecuredState) -> str:
    if state.get("guardrail_verdict") == "UNSAFE":
        return "alert"
    return "agent"


def should_continue(state: SecuredState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def build_secured_graph(checkpointer=None):
    """Build and compile the secured SCDRA graph with guardrails."""
    graph = StateGraph(SecuredState)

    graph.add_node("guardrail", guardrail_node)
    graph.add_node("agent", agent_node)
    graph.add_node("alert", alert_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("guardrail")

    graph.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {"agent": "agent", "alert": "alert"},
    )

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", END: END},
    )

    graph.add_edge("tools", "agent")
    graph.add_edge("alert", END)

    compile_kwargs = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    return graph.compile(**compile_kwargs)
