"""
graph.py — Part B: Self-RAG LangGraph StateGraph
AI407L Final Exam, Spring 2026

Implements a University Course Advisory Agent using Self-Reflective RAG.

Decision flow:
  START → decide_retrieval
    → [NO]  direct_answer → END
    → [YES] retrieve_documents → grade_relevance
                → [relevant docs]  generate_response → check_hallucination
                → [no relevant]    web_search_fallback → generate_response
                                         check_hallucination
                                           → [grounded]          END
                                           → [hallucinated, retry<3] generate_response (retry)
                                           → [hallucinated, retry≥3] END with disclaimer
"""

import json
import os
import re
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from tools import search_university_kb, search_web

LLM_MODEL   = "llama-3.3-70b-versatile"
MAX_RETRIES = 3


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────
class SelfRAGState(TypedDict):
    query:               str
    messages:            Annotated[list, add_messages]
    needs_retrieval:     bool
    retrieval_reason:    str
    retrieved_docs:      list[dict]
    relevant_docs:       list[str]
    web_results:         list[str]
    context:             list[str]
    draft_response:      str
    hallucination_detected: bool
    retry_count:         int
    final_answer:        str
    trace:               list[str]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def get_llm() -> ChatGroq:
    return ChatGroq(
        model=LLM_MODEL,
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )


def parse_json_response(text: str, default: dict) -> dict:
    """Robustly parse JSON from LLM output; fall back to default on failure."""
    text = text.strip()
    # Try extracting from markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        text = match.group(1).strip()
    # Find first {...} block
    brace_match = re.search(r"\{[\s\S]+\}", text)
    if brace_match:
        text = brace_match.group(0)
    try:
        return json.loads(text)
    except Exception:
        return default


def append_trace(state: SelfRAGState, line: str) -> list[str]:
    current = state.get("trace", [])
    return current + [line]


# ─────────────────────────────────────────────────────────────────────────────
# Node 1 — Retrieval Decision
# ─────────────────────────────────────────────────────────────────────────────
def decide_retrieval(state: SelfRAGState) -> dict:
    """LLM judge: does this query require looking up the university knowledge base?"""
    query = state["query"]
    llm   = get_llm()

    prompt = f"""You are a routing assistant for XYZ National University's course advisory system.

Determine whether the following student query requires searching the university's
knowledge base (course catalogs, academic policies, faculty directory).

Answer YES if the query is about:
- Specific courses (prerequisites, credit hours, descriptions, course codes)
- Academic policies (GPA, attendance, fees, grading scale, withdrawal deadlines)
- Faculty information (names, emails, offices, specializations)
- Department-specific information

Answer NO if the query is:
- A greeting or small talk ("Hello", "How are you?")
- A general knowledge question answerable without university data ("What does GPA stand for?")
- Completely unrelated to the university ("What is the weather today?")

Student Query: {query}

Respond with ONLY valid JSON (no markdown, no explanation):
{{"needs_retrieval": true or false, "reason": "one sentence explanation"}}"""

    result   = llm.invoke(prompt)
    parsed   = parse_json_response(result.content, {"needs_retrieval": True, "reason": "default"})
    decision = bool(parsed.get("needs_retrieval", True))
    reason   = str(parsed.get("reason", ""))

    trace_line = f"[DECISION] needs_retrieval={decision} | reason: {reason}"
    print(f"  {trace_line}")

    return {
        "needs_retrieval":  decision,
        "retrieval_reason": reason,
        "trace":            append_trace(state, trace_line),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 2 — Knowledge Base Retrieval
# ─────────────────────────────────────────────────────────────────────────────
def retrieve_documents(state: SelfRAGState) -> dict:
    """Retrieve top-4 document chunks from ChromaDB."""
    query   = state["query"]
    results = search_university_kb.invoke({"query": query, "k": 4})

    trace_line = f"[RETRIEVE] Found {len(results)} chunks from knowledge base"
    print(f"  {trace_line}")
    for i, r in enumerate(results, 1):
        src = r.get("metadata", {}).get("source", "?")
        snippet = r.get("content", "")[:60].replace("\n", " ")
        print(f"    Chunk {i}: [{src}] {snippet}...")

    return {
        "retrieved_docs": results,
        "trace":          append_trace(state, trace_line),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 3 — Relevance Grading
# ─────────────────────────────────────────────────────────────────────────────
def grade_relevance(state: SelfRAGState) -> dict:
    """Grade each retrieved document individually; keep only relevant ones."""
    query = state["query"]
    docs  = state.get("retrieved_docs", [])
    llm   = get_llm()

    relevant = []
    grades   = []

    for i, doc in enumerate(docs):
        content = doc.get("content", "")[:500]
        src     = doc.get("metadata", {}).get("source", "?")

        prompt = f"""You are a relevance grader for a university course advisory system.

Assess whether the following document chunk is RELEVANT to answering the student's query.
A document is relevant if it contains information that directly helps answer the query.

Student Query: {query}

Document (from {src}):
{content}

Respond with ONLY valid JSON:
{{"relevant": true or false, "reason": "brief explanation"}}"""

        result = llm.invoke(prompt)
        parsed = parse_json_response(result.content, {"relevant": True, "reason": ""})
        is_rel = bool(parsed.get("relevant", True))
        reason = str(parsed.get("reason", ""))
        grades.append(f"    Chunk {i+1} [{src}] -> {'RELEVANT' if is_rel else 'IRRELEVANT'}: {reason}")

        if is_rel:
            relevant.append(content)

    for g in grades:
        print(g)

    trace_line = f"[GRADE] {len(relevant)}/{len(docs)} docs relevant"
    print(f"  {trace_line}")

    return {
        "relevant_docs": relevant,
        "context":       relevant,
        "trace":         append_trace(state, trace_line),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 4 — Web Search Fallback
# ─────────────────────────────────────────────────────────────────────────────
def web_search_fallback(state: SelfRAGState) -> dict:
    """All KB docs were irrelevant — fall back to DuckDuckGo web search."""
    query   = state["query"]
    results = search_web.invoke({"query": query, "max_results": 3})

    trace_line = f"[WEB SEARCH] KB irrelevant — searched web, got {len(results)} results"
    print(f"  {trace_line}")
    for i, r in enumerate(results, 1):
        print(f"    Result {i}: {r[:80]}...")

    return {
        "web_results": results,
        "context":     results,
        "trace":       append_trace(state, trace_line),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 5 — Response Generation
# ─────────────────────────────────────────────────────────────────────────────
def generate_response(state: SelfRAGState) -> dict:
    """Generate an answer grounded strictly in the provided context."""
    query   = state["query"]
    context = state.get("context", [])
    retry   = state.get("retry_count", 0)
    llm     = get_llm()

    context_text = "\n\n---\n\n".join(context) if context else "No context available."

    retry_instruction = ""
    if retry > 0:
        retry_instruction = (
            f"\n\nIMPORTANT — RETRY ATTEMPT {retry}: "
            "Your previous answer contained unsupported claims. "
            "This time, ONLY state what is explicitly written in the context above. "
            "Do NOT add any information not present in the context."
        )

    prompt = f"""You are the University Course Advisor for XYZ National University.
Answer the student's question using ONLY the information in the provided context.
Do NOT add, infer, or fabricate any information not explicitly stated in the context.
If the context does not fully answer the question, say what you know and acknowledge the gap.

Context:
{context_text}

Student Query: {query}{retry_instruction}

Provide a clear, accurate, and helpful answer:"""

    result   = llm.invoke(prompt)
    response = result.content.strip()

    trace_line = f"[GENERATE] Draft response produced (retry={retry}, length={len(response)} chars)"
    print(f"  {trace_line}")

    return {
        "draft_response": response,
        "retry_count":    retry,
        "trace":          append_trace(state, trace_line),
        "messages":       [AIMessage(content=response)],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 6 — Hallucination Self-Check
# ─────────────────────────────────────────────────────────────────────────────
def check_hallucination(state: SelfRAGState) -> dict:
    """Verify the draft response is grounded in the context; detect hallucinations."""
    context  = state.get("context", [])
    response = state.get("draft_response", "")
    retry    = state.get("retry_count", 0)
    llm      = get_llm()

    context_text = "\n\n---\n\n".join(context) if context else "No context available."

    prompt = f"""You are a hallucination checker for a university advisory system.

Your job: verify that EVERY factual claim in the response is supported by the context below.
A claim is hallucinated if it states a specific fact (number, name, date, policy rule, etc.)
that does NOT appear in the context.

Context (ground truth):
{context_text}

Generated Response:
{response}

Respond with ONLY valid JSON:
{{
  "hallucinated": true or false,
  "unsupported_claims": ["list any specific claims not found in context, or empty list"],
  "verdict": "GROUNDED" or "HALLUCINATED"
}}"""

    result = llm.invoke(prompt)
    parsed = parse_json_response(
        result.content,
        {"hallucinated": False, "unsupported_claims": [], "verdict": "GROUNDED"},
    )
    is_hallucinated = bool(parsed.get("hallucinated", False))
    unsupported     = parsed.get("unsupported_claims", [])
    verdict         = parsed.get("verdict", "GROUNDED")

    new_retry = retry + 1 if is_hallucinated else retry

    trace_line = (
        f"[HALLUCINATION CHECK] verdict={verdict} | retry={retry}/{MAX_RETRIES}"
        + (f" | unsupported: {unsupported}" if unsupported else "")
    )
    print(f"  {trace_line}")

    # If hallucinated and retries exhausted → attach disclaimer to draft
    final = state.get("final_answer", "")
    if is_hallucinated and new_retry >= MAX_RETRIES:
        final = (
            response
            + "\n\n[DISCLAIMER] This response could not be fully verified against the "
            "source documents after 3 attempts. Please verify with the Registrar's Office."
        )
        trace_disclaimer = f"[DISCLAIMER] Max retries ({MAX_RETRIES}) reached - adding disclaimer"
        print(f"  {trace_disclaimer}")
        updated_trace = append_trace(state, trace_line) + [trace_disclaimer]
        return {
            "hallucination_detected": True,
            "retry_count":            new_retry,
            "final_answer":           final,
            "trace":                  updated_trace,
        }

    if not is_hallucinated:
        final = response

    return {
        "hallucination_detected": is_hallucinated,
        "retry_count":            new_retry,
        "final_answer":           final,
        "trace":                  append_trace(state, trace_line),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 7 — Direct Answer (no retrieval needed)
# ─────────────────────────────────────────────────────────────────────────────
def direct_answer(state: SelfRAGState) -> dict:
    """Answer conversational/general queries directly without KB retrieval."""
    query = state["query"]
    llm   = get_llm()

    prompt = f"""You are the University Course Advisor for XYZ National University.
The student asked a general question that does not require searching the university database.
Answer it helpfully and concisely.

Student Query: {query}"""

    result   = llm.invoke(prompt)
    response = result.content.strip()

    trace_line = "[DIRECT ANSWER] No retrieval needed — answered from general knowledge"
    print(f"  {trace_line}")

    return {
        "final_answer": response,
        "trace":        append_trace(state, trace_line),
        "messages":     [AIMessage(content=response)],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Routing Functions
# ─────────────────────────────────────────────────────────────────────────────
def route_after_decision(state: SelfRAGState) -> str:
    if state.get("needs_retrieval", True):
        return "retrieve_documents"
    return "direct_answer"


def route_after_grading(state: SelfRAGState) -> str:
    relevant = state.get("relevant_docs", [])
    if relevant:
        return "generate_response"
    return "web_search_fallback"


def route_after_hallucination(state: SelfRAGState) -> str:
    detected  = state.get("hallucination_detected", False)
    retry_cnt = state.get("retry_count", 0)
    if not detected:
        return END
    if retry_cnt < MAX_RETRIES:
        return "generate_response"
    return END


# ─────────────────────────────────────────────────────────────────────────────
# Graph Assembly
# ─────────────────────────────────────────────────────────────────────────────
def build_graph():
    builder = StateGraph(SelfRAGState)

    # Register nodes
    builder.add_node("decide_retrieval",    decide_retrieval)
    builder.add_node("retrieve_documents",  retrieve_documents)
    builder.add_node("grade_relevance",     grade_relevance)
    builder.add_node("web_search_fallback", web_search_fallback)
    builder.add_node("generate_response",   generate_response)
    builder.add_node("check_hallucination", check_hallucination)
    builder.add_node("direct_answer",       direct_answer)

    # Entry point
    builder.add_edge(START, "decide_retrieval")

    # After decision: retrieve or answer directly
    builder.add_conditional_edges(
        "decide_retrieval",
        route_after_decision,
        {"retrieve_documents": "retrieve_documents", "direct_answer": "direct_answer"},
    )

    # After retrieval: grade relevance
    builder.add_edge("retrieve_documents", "grade_relevance")

    # After grading: generate or web search
    builder.add_conditional_edges(
        "grade_relevance",
        route_after_grading,
        {"generate_response": "generate_response", "web_search_fallback": "web_search_fallback"},
    )

    # Web search always feeds into generation
    builder.add_edge("web_search_fallback", "generate_response")

    # After generation: check for hallucinations
    builder.add_edge("generate_response", "check_hallucination")

    # After hallucination check: done, retry, or done-with-disclaimer
    builder.add_conditional_edges(
        "check_hallucination",
        route_after_hallucination,
        {"generate_response": "generate_response", END: END},
    )

    # Direct answer goes straight to END
    builder.add_edge("direct_answer", END)

    return builder.compile()


# Export compiled graph
graph = build_graph()
