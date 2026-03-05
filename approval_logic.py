"""
approval_logic.py - Human-in-the-Loop (HITL) Safety Breakpoints

Lab 5: State Management & Human-in-the-Loop (HITL)
Tasks 2 & 3: Safety Breakpoint + State Editing

Demonstrates two HITL capabilities:
  1. interrupt_before: Graph pauses BEFORE executing a world-changing tool
     (send_notification or update_purchase_order), showing the user what
     the agent intends to do and waiting for human approval.

  2. State editing (Task 3): The human can not just approve/cancel but also
     EDIT the agent's proposed action before it executes. The agent then
     sends the human-edited version.

How interrupt_before works in LangGraph:
  - Graph is compiled with interrupt_before=["tools"]
  - When the agent generates a tool_call, the graph pauses BEFORE executing it
  - graph.get_state(config) retrieves the paused state for inspection
  - The human reviews the pending tool call and chooses: Proceed / Cancel / Edit
  - graph.invoke(None, config) resumes execution from the saved checkpoint

Usage:
    python approval_logic.py
"""

import json
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

from tools import ALL_TOOLS

load_dotenv()

# ─────────────────────────────────────────────────────────────────────
# World-changing tools that require human approval before execution
# ─────────────────────────────────────────────────────────────────────

WORLD_CHANGING_TOOLS = {"send_notification", "update_purchase_order"}


# ═══════════════════════════════════════════════════════════════════════
#  State & LLM
# ═══════════════════════════════════════════════════════════════════════

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


SYSTEM_PROMPT = """You are the Supply Chain Disruption Response Agent (SCDRA).
When asked to respond to a disruption:
1. First gather necessary data using your read-only tools.
2. Draft a response plan.
3. Then send a notification to the procurement team summarizing the situation and plan.
Always proceed through all steps — gather data, plan, then notify.
"""

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)
llm_with_tools = llm.bind_tools(ALL_TOOLS)


def agent_node(state: State) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def route_agent_output(state: State) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


tool_node = ToolNode(ALL_TOOLS)

HITL_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkpoint_db.sqlite")


def build_hitl_graph(checkpointer):
    """Build the graph with interrupt_before=['tools'].

    The graph will pause BEFORE executing ANY tool call, allowing the
    human to inspect and approve/cancel/edit world-changing actions.
    """
    graph = StateGraph(State)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_agent_output)
    graph.add_edge("tools", "agent")

    # interrupt_before="tools" pauses before every tool execution
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["tools"],
    )


# ═══════════════════════════════════════════════════════════════════════
#  HITL Helpers
# ═══════════════════════════════════════════════════════════════════════

def get_pending_tool_calls(app, config: dict) -> list[dict]:
    """Retrieve the pending tool calls from the paused state."""
    state = app.get_state(config)
    messages = state.values.get("messages", [])
    if messages:
        last = messages[-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return last.tool_calls
    return []


def is_world_changing(tool_calls: list[dict]) -> bool:
    """Return True if any pending tool call is world-changing."""
    return any(tc["name"] in WORLD_CHANGING_TOOLS for tc in tool_calls)


def display_pending_action(tool_calls: list[dict]) -> None:
    """Print a human-readable preview of the pending tool calls."""
    print("\n" + "!" * 60)
    print("  [!] SAFETY BREAKPOINT - Human Approval Required")
    print("!" * 60)
    for tc in tool_calls:
        marker = "[WORLD-CHANGING]" if tc["name"] in WORLD_CHANGING_TOOLS else "[read-only]"
        print(f"\n  Tool: {tc['name']} {marker}")
        print(f"  Args:")
        for k, v in tc.get("args", {}).items():
            val_str = str(v)[:200]
            print(f"    {k}: {val_str}")
    print("!" * 60)


def request_human_approval(tool_calls: list[dict]) -> tuple[str, dict]:
    """Interactively ask the human to approve, cancel, or edit the action.

    Returns:
        ("proceed", original_tool_calls) - run as-is
        ("cancel", {}) - abort the tool call
        ("edit", modified_tool_calls) - run with human edits
    """
    if not is_world_changing(tool_calls):
        # Non-world-changing tools auto-approve
        print("\n  [Auto-approved: read-only tool]")
        return "proceed", tool_calls

    # For demo purposes: simulate human input programmatically
    # In a real deployment this would be input() or a UI callback
    print("\n  Simulating human review...")
    print("  -> Human chooses: EDIT (modify notification message before sending)")

    # Demonstrate state editing: find the send_notification call and modify its message
    modified = []
    for tc in tool_calls:
        if tc["name"] == "send_notification":
            edited_tc = dict(tc)
            edited_tc["args"] = dict(tc["args"])
            original_msg = tc["args"].get("message", "")
            edited_tc["args"]["message"] = (
                original_msg[:200] + " [EDITED BY HUMAN: Please CC the VP of Operations.]"
            )
            modified.append(edited_tc)
            print(f"\n  [Human edited] message now includes: "
                  f"'[EDITED BY HUMAN: Please CC the VP of Operations.]'")
        else:
            modified.append(tc)

    return "edit", modified


# ═══════════════════════════════════════════════════════════════════════
#  Main HITL Loop
# ═══════════════════════════════════════════════════════════════════════

def run_with_hitl(app, initial_query: str, config: dict) -> None:
    """Run the graph with HITL approval at every tool interrupt.

    Each time the graph pauses (interrupt_before="tools"), we:
      1. Retrieve and display the pending tool calls
      2. Ask the human to approve / cancel / edit
      3. Either resume (proceed), cancel (inject rejection), or edit state
    """
    print(f"\n[User] {initial_query}\n")

    # Start the graph — it will pause at the first tool call
    app.invoke({"messages": [HumanMessage(content=initial_query)]}, config)

    iteration = 0
    max_iterations = 15  # Safety limit

    while iteration < max_iterations:
        iteration += 1

        # Check current graph state
        current_state = app.get_state(config)

        # If graph has no next nodes, it's finished
        if not current_state.next:
            print("\n[Graph] Execution complete.")
            break

        # Get pending tool calls
        tool_calls = get_pending_tool_calls(app, config)

        if not tool_calls:
            # No tool calls in pending state — resume to let agent continue
            result = app.invoke(None, config)
            continue

        # Display what the agent wants to do
        display_pending_action(tool_calls)

        # Get human decision
        decision, updated_calls = request_human_approval(tool_calls)

        if decision == "cancel":
            # Inject a rejection message into state so agent knows it was denied
            rejection = ToolMessage(
                content="[HUMAN REJECTED] This action was not approved by the human operator.",
                tool_call_id=tool_calls[0]["id"],
            )
            app.update_state(config, {"messages": [rejection]})
            print("\n  [Human] Action CANCELLED.")

        elif decision == "edit":
            # Update the pending AIMessage's tool calls with human edits
            messages = current_state.values["messages"]
            last_ai_msg = messages[-1]

            # Replace tool_calls in the AIMessage with the edited version
            edited_ai_msg = AIMessage(
                content=last_ai_msg.content or "",
                tool_calls=updated_calls,
                id=last_ai_msg.id,
            )
            app.update_state(config, {"messages": [edited_ai_msg]})
            print("\n  [Human] Edits applied. Resuming with modified action.")

        else:
            print("\n  [Human] Action APPROVED. Resuming.")

        # Resume the graph from the checkpoint
        app.invoke(None, config)

    # Print final agent response
    final_state = app.get_state(config)
    messages = final_state.values.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            print(f"\n{'=' * 60}")
            print("  Final Agent Response")
            print(f"{'=' * 60}")
            print(msg.content[:800] + ("..." if len(msg.content) > 800 else ""))
            break


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  SCDRA Human-in-the-Loop (HITL) Safety Breakpoints")
    print("  Lab 5: Task 2 (interrupt_before) + Task 3 (state editing)")
    print("=" * 60)
    print("\nConfiguration: interrupt_before=['tools']")
    print("World-changing tools requiring approval:", list(WORLD_CHANGING_TOOLS))

    with SqliteSaver.from_conn_string(HITL_DB) as checkpointer:
        app = build_hitl_graph(checkpointer)

        THREAD_ID = "hitl-demo-session-001"
        config = {
            "configurable": {"thread_id": THREAD_ID},
            "recursion_limit": 25,
        }

        scenario = (
            "TPA-001 has been hit by a logistics delay of 3 weeks. "
            "Check what inventory is affected, find backup suppliers, "
            "draft a response plan, and then notify the procurement-team "
            "and logistics-ops via Slack."
        )

        run_with_hitl(app, scenario, config)

        print(f"\n{'=' * 60}")
        print("  HITL Demo Complete")
        print(f"  Checkpoint DB: {HITL_DB}")
        print(f"  Thread: {THREAD_ID}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
