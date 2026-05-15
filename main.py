"""
Lab 8 — FastAPI server for the Supply Chain Disruption Response Agent.

Provides REST API endpoints:
  - POST /chat   — Invoke the agent and return full response
  - POST /stream — Stream the agent's response node-by-node via SSE

Run:
    uvicorn main:app --host 0.0.0.0 --port 8000
    # or: python main.py
"""

import json
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

from schema import ChatRequest, ChatResponse, ToolCallInfo
from graph import build_graph, SYSTEM_PROMPT


app = FastAPI(title="SCDRA — Supply Chain Disruption Response Agent", version="1.0.0")


# ── Helpers ──────────────────────────────────────────────────────────────

def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [p["text"] for p in content if isinstance(p, dict) and p.get("type") == "text"]
        return "\n".join(parts)
    return str(content)


# ── POST /chat ───────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Invoke the SCDRA agent and return the full response."""
    try:
        if req.mode == "multi":
            from multi_agent_graph import build_multi_agent_graph
            graph = build_multi_agent_graph()
        else:
            graph = build_graph()

        result = graph.invoke(
            {"messages": [HumanMessage(content=req.message)]},
            {"recursion_limit": 25},
        )

        tool_calls = []
        final_response = ""
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append(ToolCallInfo(name=tc["name"], args=tc["args"]))
            if isinstance(msg, AIMessage):
                text = _extract_text(msg.content)
                if text.strip():
                    final_response = text

        return ChatResponse(
            response=final_response,
            tool_calls=tool_calls,
            mode=req.mode,
            thread_id=req.thread_id,
            status="success",
        )
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "rate" in error_msg.lower():
            return JSONResponse(status_code=429, content={
                "error": "Rate limit exceeded. Please wait and try again.",
            })
        return JSONResponse(status_code=500, content={"error": f"Agent error: {error_msg}"})


# ── POST /stream ─────────────────────────────────────────────────────────

@app.post("/stream")
async def stream_chat(req: ChatRequest):
    """Stream the agent's response node-by-node using SSE."""
    async def event_generator():
        try:
            if req.mode == "multi":
                from multi_agent_graph import build_multi_agent_graph
                graph = build_multi_agent_graph()
            else:
                graph = build_graph()

            input_state = {"messages": [HumanMessage(content=req.message)]}

            for event in graph.stream(input_state, {"recursion_limit": 25}):
                for node_name, node_output in event.items():
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                data = json.dumps({
                                    "type": "tool_call",
                                    "node": node_name,
                                    "tool": tc["name"],
                                    "args": tc["args"],
                                })
                                yield f"data: {data}\n\n"
                        elif isinstance(msg, AIMessage):
                            text = _extract_text(msg.content)
                            if text.strip():
                                data = json.dumps({
                                    "type": "agent_response",
                                    "node": node_name,
                                    "content": text,
                                })
                                yield f"data: {data}\n\n"
                        elif hasattr(msg, "content") and hasattr(msg, "name") and msg.name:
                            data = json.dumps({
                                "type": "tool_result",
                                "node": node_name,
                                "tool": msg.name,
                                "content": _extract_text(msg.content)[:500],
                            })
                            yield f"data: {data}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ── Entry Point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n  SCDRA API Server")
    print("  http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
