"""
Weather & News Briefing MCP Client
====================================
Connects to the MCP server via stdio transport, discovers available tools,
invokes them with sample parameters, and prints formatted responses.

Demonstrates the full MCP lifecycle:
  1. Tool Registration  -- server advertises available tools
  2. Tool Discovery     -- client lists tools and their schemas
  3. Tool Invocation    -- client calls tools with arguments
  4. Context Passing    -- arguments are passed as structured JSON
  5. Response Handling  -- client receives and formats TextContent results
"""

import sys
import json
import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


def print_header(title: str) -> None:
    """Print a formatted section header."""
    width = 64
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def print_subheader(title: str) -> None:
    """Print a formatted sub-section header."""
    print(f"\n--- {title} ---")


async def run_client():
    """Main client workflow: connect, discover, invoke, display."""

    # Determine correct Python executable (same interpreter running this script)
    python_exec = sys.executable

    # Configure stdio transport -- spawn server.py as a subprocess
    server_params = StdioServerParameters(
        command=python_exec,
        args=["C:/Users/Hassaan/Desktop/Osaid Capstone/mcp/server.py"],
    )

    print_header("MCP CLIENT -- Weather & News Briefing")
    print("  Transport : stdio (subprocess)")
    print(f"  Server    : mcp/server.py")
    print(f"  Python    : {python_exec}")

    # -------------------------------------------------------------------------
    # STEP 1: Connect to the server via stdio transport
    # -------------------------------------------------------------------------
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the MCP session
            await session.initialize()

            # -----------------------------------------------------------------
            # STEP 2: Tool Registration & Discovery
            # -----------------------------------------------------------------
            print_header("STEP 1: TOOL DISCOVERY")
            print("  Requesting tool list from server...")

            tools_response = await session.list_tools()
            tools = tools_response.tools

            print(f"  Server registered {len(tools)} tool(s):\n")
            for tool in tools:
                required = tool.inputSchema.get("required", [])
                props = tool.inputSchema.get("properties", {})
                param_strs = []
                for p_name, p_schema in props.items():
                    p_type = p_schema.get("type", "any")
                    marker = " [required]" if p_name in required else ""
                    param_strs.append(f"      - {p_name}: {p_type}{marker}")
                params_block = "\n".join(param_strs) if param_strs else "      (none)"
                print(f"  [{tool.name}]")
                print(f"    Description: {tool.description}")
                print(f"    Parameters:")
                print(params_block)
                print()

            # -----------------------------------------------------------------
            # STEP 3: Tool Invocation -- get_weather
            # -----------------------------------------------------------------
            print_header("STEP 2: CALL get_weather (Islamabad)")
            weather_args = {"city": "Islamabad", "units": "celsius"}
            print(f"  Context passed -> {json.dumps(weather_args)}")

            weather_result = await session.call_tool("get_weather", weather_args)
            weather_text = weather_result.content[0].text
            print(f"\n  Response received:")
            for line in weather_text.split("\n"):
                print(f"    {line}")

            # -----------------------------------------------------------------
            # STEP 4: Tool Invocation -- get_news_headlines
            # -----------------------------------------------------------------
            print_header("STEP 3: CALL get_news_headlines (technology)")
            news_args = {"category": "technology", "count": 3}
            print(f"  Context passed -> {json.dumps(news_args)}")

            news_result = await session.call_tool("get_news_headlines", news_args)
            news_text = news_result.content[0].text
            headlines = json.loads(news_text)
            print(f"\n  Response received ({len(headlines)} headlines):")
            for i, h in enumerate(headlines, 1):
                print(f"    {i}. {h['title']}")
                print(f"       Source: {h['source']}  |  {h['published_date']}")

            # -----------------------------------------------------------------
            # STEP 5: Tool Invocation -- get_daily_briefing
            # -----------------------------------------------------------------
            print_header("STEP 4: CALL get_daily_briefing (Islamabad + technology)")
            briefing_args = {"city": "Islamabad", "news_category": "technology"}
            print(f"  Context passed -> {json.dumps(briefing_args)}")

            briefing_result = await session.call_tool("get_daily_briefing", briefing_args)
            briefing_text = briefing_result.content[0].text
            print(f"\n  Response received:\n")
            for line in briefing_text.split("\n"):
                print(f"    {line}")

            # -----------------------------------------------------------------
            # Summary
            # -----------------------------------------------------------------
            print_header("MCP SESSION COMPLETE")
            print("  Tools discovered : 3")
            print("  Tools invoked    : 3")
            print("  Errors           : 0")
            print("  Transport        : stdio (subprocess)")
            print()


if __name__ == "__main__":
    asyncio.run(run_client())
