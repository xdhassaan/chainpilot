"""
mcp_client.py - MCP Client for Academic Text Analysis

Mid-Term Exam Part B, Task 2 (10 marks)
AI407L Spring 2026

Demonstrates the full MCP client lifecycle:
  1. Connection  - Launches mcp_server.py as a subprocess and establishes
                   a stdio MCP session
  2. Handshake   - session.initialize() performs the MCP capability exchange
  3. Discovery   - session.list_tools() retrieves all tools the server advertises
  4. Invocation  - session.call_tool() invokes each tool with arguments
  5. Response    - Structured JSON responses are parsed and displayed

This client is intentionally standalone — it does NOT import any LangGraph,
LangChain, or supply chain code from Part A.

Usage:
    python mcp_client.py
    (The client spawns the server automatically as a subprocess)
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ============================================================
#  Sample academic text for demonstration
# ============================================================

SAMPLE_TEXT = """
Supply chain resilience research has gained considerable traction in the aftermath
of global disruptions. Scholars argue that organisations must develop dynamic
capabilities to anticipate, adapt to, and recover from unforeseen shocks.
Empirical studies suggest that firms investing in supplier diversification,
real-time visibility platforms, and digital twins experience significantly lower
recovery times compared to those relying on single-source procurement strategies.
Furthermore, the integration of artificial intelligence into inventory management
systems enables predictive disruption detection, allowing procurement teams to
activate contingency protocols before critical shortfalls materialise.
The evidence collectively underscores the importance of proactive risk governance
frameworks rather than reactive crisis management approaches.
"""


# ============================================================
#  Display Helpers
# ============================================================

def print_banner(title: str) -> None:
    line = "=" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(line)


def print_section(label: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {label}")
    print(f"{'-' * 60}")


def display_tool_list(tools) -> None:
    print_section("Step 3 — Tool Discovery (session.list_tools())")
    print(f"  Server advertises {len(tools)} tool(s):\n")
    for i, tool in enumerate(tools, 1):
        print(f"  [{i}] Tool Name : {tool.name}")
        print(f"      Description: {tool.description[:120]}...")
        schema_props = tool.inputSchema.get("properties", {})
        print(f"      Inputs     : {list(schema_props.keys())}")
        print()


def display_tool_result(tool_name: str, result) -> None:
    print(f"\n  [Result: {tool_name}]")
    for content in result.content:
        try:
            parsed = json.loads(content.text)
            print(json.dumps(parsed, indent=4))
        except (json.JSONDecodeError, AttributeError):
            print(f"  {content}")


# ============================================================
#  Main MCP Client Session
# ============================================================

async def run_client() -> None:
    print_banner("MCP Client — Academic Text Analysis")
    print("  Mid-Term Exam Part B | AI407L Spring 2026")
    print("  Protocol : Model Context Protocol (MCP) over stdio")

    # ── Step 1: Connection ─────────────────────────────────────
    print_section("Step 1 — Connection")
    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")
    print(f"  Launching MCP server as subprocess:")
    print(f"    Command : python {server_script}")
    print(f"  Transport: stdio (JSON-RPC over stdin/stdout)")

    server_params = StdioServerParameters(
        command=sys.executable,  # same Python interpreter
        args=[server_script],
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:

            # ── Step 2: MCP Handshake ──────────────────────────────
            print_section("Step 2 — MCP Handshake (session.initialize())")
            init_result = await session.initialize()
            print(f"  Server name       : {init_result.serverInfo.name}")
            print(f"  Protocol version  : {init_result.protocolVersion}")
            server_caps = init_result.capabilities
            print(f"  Server capabilities:")
            print(f"    tools           : {server_caps.tools is not None}")
            print(f"    resources       : {server_caps.resources is not None}")
            print(f"    prompts         : {server_caps.prompts is not None}")
            print("  [Handshake complete]")

            # ── Step 3: Tool Discovery ─────────────────────────────
            tools_response = await session.list_tools()
            display_tool_list(tools_response.tools)

            # ── Step 4 & 5: Tool Invocation + Response Display ─────
            print_section("Step 4 — Tool Invocations (session.call_tool())")
            print(f"  Sample text ({len(SAMPLE_TEXT.split())} words from fictional research paper):")
            preview = SAMPLE_TEXT.strip()[:200]
            print(f"  \"{preview}...\"")

            # --- Tool 1: analyze_text ---
            print("\n  Invoking: analyze_text")
            result1 = await session.call_tool(
                "analyze_text",
                {"text": SAMPLE_TEXT},
            )
            display_tool_result("analyze_text", result1)

            # --- Tool 2: extract_keywords (top 7) ---
            print("\n  Invoking: extract_keywords (top_n=7)")
            result2 = await session.call_tool(
                "extract_keywords",
                {"text": SAMPLE_TEXT, "top_n": 7},
            )
            display_tool_result("extract_keywords", result2)

            # --- Tool 3: score_readability ---
            print("\n  Invoking: score_readability")
            result3 = await session.call_tool(
                "score_readability",
                {"text": SAMPLE_TEXT},
            )
            display_tool_result("score_readability", result3)

            # ── Summary ───────────────────────────────────────────
            print_banner("MCP Session Complete")
            print("  All 3 tools invoked successfully via MCP protocol.")
            print()
            print("  MCP Lifecycle demonstrated:")
            print("    [1] Connection    - Server spawned as stdio subprocess")
            print("    [2] Handshake     - session.initialize() capability exchange")
            print("    [3] Discovery     - session.list_tools() returned 3 tools")
            print("    [4] Invocation    - session.call_tool() called each tool")
            print("    [5] Response      - Structured JSON results parsed and displayed")
            print()
            print("  Key MCP Properties:")
            print("    - Server runs as a separate process (true process isolation)")
            print("    - Client and server communicate over JSON-RPC / stdio")
            print("    - Tools are discovered dynamically at runtime (no hardcoding)")
            print("    - Protocol is transport-agnostic (stdio here, HTTP in production)")
            print("=" * 60)


# ============================================================
#  Entry Point
# ============================================================

if __name__ == "__main__":
    asyncio.run(run_client())
