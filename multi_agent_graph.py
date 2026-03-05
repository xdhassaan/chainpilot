"""
multi_agent_graph.py - Multi-Agent Orchestration for the SCDRA

Lab 4: Multi-Agent Orchestration (Specialized Teams)

Two specialized agents collaborate in sequence:
  - ResearcherAgent: Gathers raw supply chain intelligence (read-only tools)
  - AnalystAgent: Synthesizes findings into decisions and actions

Graph topology:
  START --> researcher --> [router] --> researcher_tools --> researcher
                              |
                              +--(handoff signal)--> analyst --> [router] --> analyst_tools --> analyst
                                                                    |
                                                                    +--(final answer)--> END

Handoff Protocol:
  The Researcher signals completion by including the phrase
  "[HANDOFF: Research complete. Passing to Analyst.]" in its final message.
  The router detects this signal and transitions to the Analyst node.
"""

import json
import os
import sys
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, AIMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from tools import (
    # Researcher tools (read-only + calculate)
    search_supplier_docs,
    query_inventory_db,
    fetch_disruption_alerts,
    load_disruption_history,
    get_supplier_pricing,
    search_sop_wiki,
    calculate_financial_impact,
    # Analyst tools (synthesize + act)
    draft_response_plan,
    send_notification,
    update_purchase_order,
)

load_dotenv()


# ═══════════════════════════════════════════════════════════════════════
#  Tool Registries — Each agent only sees its own tools
# ═══════════════════════════════════════════════════════════════════════

RESEARCHER_TOOLS = [
    search_supplier_docs,
    query_inventory_db,
    fetch_disruption_alerts,
    load_disruption_history,
    get_supplier_pricing,
    search_sop_wiki,
    calculate_financial_impact,
]

ANALYST_TOOLS = [
    draft_response_plan,
    send_notification,
    update_purchase_order,
]


# ═══════════════════════════════════════════════════════════════════════
#  State Definition
# ═══════════════════════════════════════════════════════════════════════

HANDOFF_SIGNAL = "[HANDOFF: Research complete. Passing to Analyst.]"


class State(TypedDict):
    """Multi-agent shared state.

    messages: Full conversation history (thoughts, tool calls, results)
    current_agent: Tracks which agent is currently active for routing decisions
    """
    messages: Annotated[list[AnyMessage], add_messages]
    current_agent: str


# ═══════════════════════════════════════════════════════════════════════
#  LLM Configuration
# ═══════════════════════════════════════════════════════════════════════

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)

researcher_llm = llm.bind_tools(RESEARCHER_TOOLS)
analyst_llm = llm.bind_tools(ANALYST_TOOLS)


# ═══════════════════════════════════════════════════════════════════════
#  System Prompts
# ═══════════════════════════════════════════════════════════════════════

RESEARCHER_SYSTEM_PROMPT = f"""You are the Supply Chain Researcher for an electronics manufacturing company.

Your ONLY job is to gather raw supply chain intelligence using your data tools.
You have access to: inventory databases, supplier qualification documents, disruption
alerts, historical disruption data, supplier pricing, SOPs, and financial calculators.

## Your Tools
- search_supplier_docs: Search supplier qualifications in the vector database
- query_inventory_db: Check inventory levels and open purchase orders
- fetch_disruption_alerts: Get real-time disruption alerts by region and category
- load_disruption_history: Find historical responses to similar disruption types
- get_supplier_pricing: Fetch pricing, lead times, and MOQ from suppliers
- search_sop_wiki: Retrieve relevant Standard Operating Procedures
- calculate_financial_impact: Compute cost exposure from affected orders

## Rules
1. Call tools to gather data — do not guess or make up information.
2. Use multiple tools to build a complete picture of the disruption.
3. Present all findings as factual summaries — NO recommendations.
4. When you have gathered all relevant intelligence, end your final message with EXACTLY:
   {HANDOFF_SIGNAL}
5. Do NOT draft response plans or send notifications — that is the Analyst's job.
"""

ANALYST_SYSTEM_PROMPT = """You are the Supply Chain Analyst for an electronics manufacturing company.

The Researcher has already gathered all raw data. Your job is to synthesize those
findings into a formal response plan and, where appropriate, execute approved actions.

## Your Tools
- draft_response_plan: Generate a structured action plan from gathered intelligence
- send_notification: Send alerts to stakeholders via Slack/email (WORLD-CHANGING — mock)
- update_purchase_order: Reroute purchase orders to backup suppliers (WORLD-CHANGING — mock)

## Rules
1. Read the Researcher's findings from the conversation history before acting.
2. ALWAYS call draft_response_plan first to create the structured plan.
3. After drafting the plan, you may call send_notification or update_purchase_order
   as appropriate (these are mock actions for demonstration).
4. Deliver a concise, executive-level final summary to the user.
5. Do NOT call data-gathering tools — the Researcher has already done this.
"""


# ═══════════════════════════════════════════════════════════════════════
#  Agent Nodes
# ═══════════════════════════════════════════════════════════════════════

def researcher_node(state: State) -> dict:
    """ResearcherAgent Node: gathers supply chain intelligence using read-only tools.

    Prepends the Researcher system prompt to the conversation history and invokes
    the LLM with researcher-only tools bound. Tracks the current agent as 'researcher'.
    """
    messages = [SystemMessage(content=RESEARCHER_SYSTEM_PROMPT)] + state["messages"]
    response = researcher_llm.invoke(messages)
    return {"messages": [response], "current_agent": "researcher"}


def analyst_node(state: State) -> dict:
    """AnalystAgent Node: synthesizes research into a response plan and actions.

    Prepends the Analyst system prompt and invokes the LLM with analyst-only tools
    bound. The Analyst sees the full conversation history including the Researcher's
    findings. Tracks the current agent as 'analyst'.
    """
    messages = [SystemMessage(content=ANALYST_SYSTEM_PROMPT)] + state["messages"]
    response = analyst_llm.invoke(messages)
    return {"messages": [response], "current_agent": "analyst"}


# ═══════════════════════════════════════════════════════════════════════
#  Tool Nodes (one per agent, each scoped to its tool subset)
# ═══════════════════════════════════════════════════════════════════════

researcher_tool_node = ToolNode(RESEARCHER_TOOLS)
analyst_tool_node = ToolNode(ANALYST_TOOLS)


# ═══════════════════════════════════════════════════════════════════════
#  Conditional Routers
# ═══════════════════════════════════════════════════════════════════════

def route_researcher(state: State) -> str:
    """Router for the Researcher node.

    Three possible routes:
    1. LLM wants to call tools → 'researcher_tools'
    2. LLM's message contains the handoff signal → 'analyst' (transition)
    3. LLM produced a final answer without handoff signal → END (fallback)
    """
    last_message = state["messages"][-1]

    # If the Researcher wants to call more tools, let it
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "researcher_tools"

    # Check for the handoff signal in the final text
    if hasattr(last_message, "content") and HANDOFF_SIGNAL in last_message.content:
        return "analyst"

    # Fallback: if researcher stopped without signal, still pass to analyst
    return "analyst"


def route_analyst(state: State) -> str:
    """Router for the Analyst node.

    Two possible routes:
    1. LLM wants to call tools (draft plan, send notification, etc.) → 'analyst_tools'
    2. LLM produced a final answer → END
    """
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "analyst_tools"

    return END


# ═══════════════════════════════════════════════════════════════════════
#  Graph Construction & Compilation
# ═══════════════════════════════════════════════════════════════════════

def build_multi_agent_graph():
    """Construct and compile the multi-agent LangGraph.

    Topology::

        START
          |
          v
        researcher --> [route_researcher] --> researcher_tools --> researcher
                              |
                              +--(handoff / fallback) --> analyst --> [route_analyst] --> analyst_tools --> analyst
                                                                              |
                                                                              +--(final answer) --> END
    """
    graph = StateGraph(State)

    # Add agent nodes
    graph.add_node("researcher", researcher_node)
    graph.add_node("analyst", analyst_node)

    # Add tool nodes
    graph.add_node("researcher_tools", researcher_tool_node)
    graph.add_node("analyst_tools", analyst_tool_node)

    # Edges: START → researcher
    graph.add_edge(START, "researcher")

    # Researcher loop: researcher → [router] → researcher_tools → researcher
    graph.add_conditional_edges("researcher", route_researcher)
    graph.add_edge("researcher_tools", "researcher")

    # Analyst loop: analyst → [router] → analyst_tools → analyst
    graph.add_conditional_edges("analyst", route_analyst)
    graph.add_edge("analyst_tools", "analyst")

    return graph.compile()


app = build_multi_agent_graph()


# ═══════════════════════════════════════════════════════════════════════
#  Pretty-Print Trace
# ═══════════════════════════════════════════════════════════════════════

def print_trace(result: dict) -> None:
    """Print a formatted trace of the multi-agent collaboration."""
    current_agent_label = "Researcher"

    for msg in result["messages"]:
        role = msg.__class__.__name__.replace("Message", "")

        if role == "Human":
            print(f"\n{'=' * 60}")
            print(f"[USER]\n{msg.content}")
            print(f"{'=' * 60}")

        elif role == "AI":
            # Detect agent switch by checking for handoff signal
            if hasattr(msg, "content") and HANDOFF_SIGNAL in (msg.content or ""):
                current_agent_label = "Researcher → HANDOFF"
            elif current_agent_label in ("Researcher → HANDOFF", "Analyst"):
                current_agent_label = "Analyst"

            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"\n[{current_agent_label.upper()} — Tool Calls]")
                for tc in msg.tool_calls:
                    args_str = json.dumps(tc.get("args", {}), indent=2)
                    truncated = args_str[:200] + ("..." if len(args_str) > 200 else "")
                    print(f"  → {tc['name']}({truncated})")
            elif hasattr(msg, "content") and msg.content:
                print(f"\n[{current_agent_label.upper()} — Response]")
                preview = msg.content[:600]
                print(preview + ("..." if len(msg.content) > 600 else ""))

            # After printing handoff message, switch label for next messages
            if current_agent_label == "Researcher → HANDOFF":
                current_agent_label = "Analyst"

        elif role == "Tool":
            if hasattr(msg, "content") and msg.content:
                preview = msg.content[:200]
                print(f"\n  [Tool Result: {getattr(msg, 'name', 'unknown')}]")
                print(f"  {preview}{'...' if len(msg.content) > 200 else ''}")


# ═══════════════════════════════════════════════════════════════════════
#  Main — Run collaboration test
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  SCDRA Multi-Agent Collaboration")
    print("  Researcher -> Analyst Handoff")
    print("  Lab 4: Multi-Agent Orchestration")
    print("=" * 60)

    test_scenario = (
        "URGENT: Our primary supplier TPA-001 (TechParts Asia) in Shenzhen has "
        "suffered a factory fire and cannot fulfill orders for the next 30 days. "
        "We have open purchase orders PO-2024-001 and PO-2024-002 with them. "
        "Please investigate the impact, identify alternative suppliers, assess "
        "our financial exposure, and produce a formal response plan."
    )

    print(f"\nScenario: {test_scenario}\n")

    result = app.invoke(
        {
            "messages": [HumanMessage(content=test_scenario)],
            "current_agent": "researcher",
        },
        {"recursion_limit": 30},
    )

    print_trace(result)

    print(f"\n{'=' * 60}")
    print("Multi-agent collaboration complete.")
    print(f"Total messages in state: {len(result['messages'])}")
    print(f"Final active agent: {result.get('current_agent', 'unknown')}")
    print(f"{'=' * 60}")
