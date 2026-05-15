"""
Weather & News Briefing MCP Server
===================================
An MCP (Model Context Protocol) server that exposes structured tools
for weather lookup and news headlines retrieval via stdio transport.

Layers:
  - Model Layer:      Pre-defined data dictionaries (weather, news)
  - Context Layer:    Input validation and parameter resolution
  - Tools Layer:      Tool definitions with JSON schemas
  - Execution Layer:  Tool dispatch and response formatting
"""

import json
import asyncio
from datetime import datetime, timedelta
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# =============================================================================
# MODEL LAYER -- Static/simulated data representing external data sources
# =============================================================================

WEATHER_DATA: dict[str, dict] = {
    "new york": {
        "city": "New York",
        "temperature_c": 12,
        "condition": "Partly Cloudy",
        "humidity": 62,
        "wind_speed_kmh": 18,
    },
    "london": {
        "city": "London",
        "temperature_c": 9,
        "condition": "Overcast",
        "humidity": 78,
        "wind_speed_kmh": 24,
    },
    "tokyo": {
        "city": "Tokyo",
        "temperature_c": 18,
        "condition": "Clear Sky",
        "humidity": 55,
        "wind_speed_kmh": 10,
    },
    "san francisco": {
        "city": "San Francisco",
        "temperature_c": 15,
        "condition": "Foggy",
        "humidity": 80,
        "wind_speed_kmh": 14,
    },
    "islamabad": {
        "city": "Islamabad",
        "temperature_c": 28,
        "condition": "Sunny",
        "humidity": 40,
        "wind_speed_kmh": 8,
    },
}

NEWS_HEADLINES: dict[str, list[dict]] = {
    "technology": [
        {"title": "AI-Powered Code Assistants See 300% Adoption Surge in 2026", "source": "TechCrunch", "published_date": "2026-03-09"},
        {"title": "Quantum Computing Breakthrough: 1000-Qubit Processor Achieved", "source": "Wired", "published_date": "2026-03-08"},
        {"title": "Open-Source LLM Framework Surpasses GPT-5 on Key Benchmarks", "source": "Ars Technica", "published_date": "2026-03-08"},
        {"title": "EU Passes Landmark AI Transparency Regulation", "source": "The Verge", "published_date": "2026-03-07"},
        {"title": "SpaceX Starlink V3 Delivers 1Gbps to Rural Communities", "source": "Reuters", "published_date": "2026-03-07"},
    ],
    "business": [
        {"title": "Global Markets Rally as Fed Signals Rate Cuts", "source": "Bloomberg", "published_date": "2026-03-09"},
        {"title": "Tesla Unveils $18,000 Compact EV for Emerging Markets", "source": "CNBC", "published_date": "2026-03-08"},
        {"title": "Saudi Aramco Invests $50B in Green Hydrogen Infrastructure", "source": "Financial Times", "published_date": "2026-03-08"},
        {"title": "Remote Work Hits All-Time High: 45% of Global Workforce", "source": "Forbes", "published_date": "2026-03-07"},
        {"title": "Stripe IPO Valued at $95 Billion in Largest Tech Listing of 2026", "source": "Wall Street Journal", "published_date": "2026-03-07"},
    ],
    "sports": [
        {"title": "Pakistan Clinches T20 Series Against Australia 3-1", "source": "ESPN Cricinfo", "published_date": "2026-03-09"},
        {"title": "Champions League Quarter-Finals Draw Produces Blockbuster Ties", "source": "BBC Sport", "published_date": "2026-03-08"},
        {"title": "Djokovic Announces Retirement After Record 25th Grand Slam", "source": "Sky Sports", "published_date": "2026-03-08"},
        {"title": "NBA: Lakers Complete Historic Comeback in Western Conference", "source": "ESPN", "published_date": "2026-03-07"},
        {"title": "2026 FIFA World Cup Ticket Sales Surpass 5 Million", "source": "Reuters", "published_date": "2026-03-07"},
    ],
    "world": [
        {"title": "UN Climate Summit Reaches Binding Emissions Agreement", "source": "BBC News", "published_date": "2026-03-09"},
        {"title": "G20 Nations Agree on Global Minimum Digital Services Tax", "source": "Al Jazeera", "published_date": "2026-03-08"},
        {"title": "Japan Launches World's First Commercial Fusion Reactor", "source": "Reuters", "published_date": "2026-03-08"},
        {"title": "African Union Free Trade Zone Reports Record Intra-Continental Trade", "source": "The Guardian", "published_date": "2026-03-07"},
        {"title": "WHO Declares End of Latest Global Health Emergency", "source": "Associated Press", "published_date": "2026-03-07"},
    ],
}

# =============================================================================
# CONTEXT LAYER -- Input validation and parameter resolution
# =============================================================================


def resolve_weather_params(arguments: dict) -> tuple[str, str]:
    """Validate and resolve weather tool parameters."""
    city = arguments.get("city", "").strip().lower()
    units = arguments.get("units", "celsius").strip().lower()
    if city not in WEATHER_DATA:
        available = ", ".join(d["city"] for d in WEATHER_DATA.values())
        raise ValueError(f"City '{arguments.get('city')}' not found. Available cities: {available}")
    if units not in ("celsius", "fahrenheit"):
        raise ValueError(f"Units must be 'celsius' or 'fahrenheit', got '{units}'")
    return city, units


def resolve_news_params(arguments: dict) -> tuple[str, int]:
    """Validate and resolve news tool parameters."""
    category = arguments.get("category", "").strip().lower()
    count = int(arguments.get("count", 3))
    if category not in NEWS_HEADLINES:
        available = ", ".join(NEWS_HEADLINES.keys())
        raise ValueError(f"Category '{arguments.get('category')}' not found. Available: {available}")
    if not 1 <= count <= 5:
        raise ValueError(f"Count must be between 1 and 5, got {count}")
    return category, count


# =============================================================================
# EXECUTION LAYER -- Business logic that produces results
# =============================================================================


def execute_get_weather(city: str, units: str) -> dict:
    """Produce weather result for a validated city and unit system."""
    data = WEATHER_DATA[city].copy()
    temp_c = data["temperature_c"]
    if units == "fahrenheit":
        data["temperature"] = round(temp_c * 9 / 5 + 32, 1)
        data["units"] = "fahrenheit"
    else:
        data["temperature"] = temp_c
        data["units"] = "celsius"
    del data["temperature_c"]
    return data


def execute_get_news(category: str, count: int) -> list[dict]:
    """Return the requested number of headlines for a validated category."""
    return NEWS_HEADLINES[category][:count]


def execute_get_daily_briefing(city: str, news_category: str) -> str:
    """Combine weather and news into a formatted daily briefing string."""
    weather = execute_get_weather(city, "celsius")
    headlines = execute_get_news(news_category, 3)

    lines = [
        "=" * 60,
        f"  DAILY BRIEFING  --  {datetime.now().strftime('%A, %B %d, %Y')}",
        "=" * 60,
        "",
        "--- WEATHER ---",
        f"  Location   : {weather['city']}",
        f"  Temperature: {weather['temperature']} C",
        f"  Condition  : {weather['condition']}",
        f"  Humidity   : {weather['humidity']}%",
        f"  Wind Speed : {weather['wind_speed_kmh']} km/h",
        "",
        f"--- TOP {news_category.upper()} NEWS ---",
    ]
    for i, h in enumerate(headlines, 1):
        lines.append(f"  {i}. {h['title']}")
        lines.append(f"     Source: {h['source']}  |  {h['published_date']}")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


# =============================================================================
# TOOLS LAYER -- MCP tool definitions (JSON schemas) and dispatch
# =============================================================================

app = Server("weather-news-briefing")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Register and expose all available tools with their JSON schemas."""
    return [
        Tool(
            name="get_weather",
            description="Get current weather information for a supported city.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (New York, London, Tokyo, San Francisco, Islamabad)",
                    },
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "default": "celsius",
                        "description": "Temperature unit system",
                    },
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="get_news_headlines",
            description="Retrieve recent news headlines for a given category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["technology", "business", "sports", "world"],
                        "description": "News category to retrieve headlines for",
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "default": 3,
                        "description": "Number of headlines to return (1-5)",
                    },
                },
                "required": ["category"],
            },
        ),
        Tool(
            name="get_daily_briefing",
            description="Get a combined daily briefing with weather and top news headlines.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City for weather information",
                    },
                    "news_category": {
                        "type": "string",
                        "enum": ["technology", "business", "sports", "world"],
                        "description": "News category for headlines",
                    },
                },
                "required": ["city", "news_category"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch tool calls to the appropriate execution handler."""
    try:
        if name == "get_weather":
            city, units = resolve_weather_params(arguments)
            result = execute_get_weather(city, units)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_news_headlines":
            category, count = resolve_news_params(arguments)
            result = execute_get_news(category, count)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_daily_briefing":
            city_key = arguments.get("city", "").strip().lower()
            news_cat = arguments.get("news_category", "").strip().lower()
            # Validate both sub-parameters
            if city_key not in WEATHER_DATA:
                available = ", ".join(d["city"] for d in WEATHER_DATA.values())
                raise ValueError(f"City '{arguments.get('city')}' not found. Available: {available}")
            if news_cat not in NEWS_HEADLINES:
                available = ", ".join(NEWS_HEADLINES.keys())
                raise ValueError(f"Category '{arguments.get('news_category')}' not found. Available: {available}")
            result = execute_get_daily_briefing(city_key, news_cat)
            return [TextContent(type="text", text=result)]

        else:
            return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

    except ValueError as exc:
        return [TextContent(type="text", text=f"Validation Error: {exc}")]
    except Exception as exc:
        return [TextContent(type="text", text=f"Internal Error: {exc}")]


# =============================================================================
# ENTRY POINT -- Run the server over stdio transport
# =============================================================================

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
