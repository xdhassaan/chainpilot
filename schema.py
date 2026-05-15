"""
Lab 8 — Pydantic schemas for the FastAPI REST endpoints.

Defines the request and response contracts for the /chat and /stream
endpoints, ensuring strict validation of client payloads.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for POST /chat and POST /stream."""
    message: str = Field(
        ...,
        description="The user's message to the SCDRA agent.",
        min_length=1,
        max_length=2000,
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional thread ID for persistent conversations.",
    )
    mode: str = Field(
        default="single",
        description="Agent mode: 'single' for ReAct agent, 'multi' for multi-agent.",
        pattern="^(single|multi)$",
    )


class ToolCallInfo(BaseModel):
    name: str = Field(description="Name of the tool that was called.")
    args: dict = Field(description="Arguments passed to the tool.")


class ChatResponse(BaseModel):
    response: str = Field(description="The agent's final response text.")
    tool_calls: list[ToolCallInfo] = Field(default_factory=list)
    mode: str = Field(description="Agent mode used.")
    thread_id: Optional[str] = Field(default=None)
    status: str = Field(default="success")


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
