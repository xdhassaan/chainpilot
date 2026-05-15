"""
tools.py — Part B: Self-RAG Agent Tool Definitions
AI407L Final Exam, Spring 2026

Defines @tool-decorated functions with Pydantic validation for:
  1. search_university_kb — ChromaDB vector search over university catalogs
  2. search_web           — DuckDuckGo web search fallback
"""

import os
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION  = "university_catalog"
EMBED_MODEL = "all-MiniLM-L6-v2"


# ─────────────────────────────────────────────────────────────────────────────
# Shared ChromaDB accessor (lazy-loaded, reused across calls)
# ─────────────────────────────────────────────────────────────────────────────
_vectorstore = None


def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        from langchain_chroma import Chroma
        from langchain_community.embeddings import SentenceTransformerEmbeddings
        _vectorstore = Chroma(
            collection_name=COLLECTION,
            persist_directory=CHROMA_DIR,
            embedding_function=SentenceTransformerEmbeddings(model_name=EMBED_MODEL),
        )
    return _vectorstore


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 — Knowledge Base Search
# ─────────────────────────────────────────────────────────────────────────────
class KBSearchInput(BaseModel):
    query: str = Field(
        description="Natural-language search query against the XYZ National University "
                    "knowledge base (courses, prerequisites, policies, faculty, fees)."
    )
    k: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Number of document chunks to retrieve (default 4, max 10).",
    )


@tool(args_schema=KBSearchInput)
def search_university_kb(query: str, k: int = 4) -> list[dict]:
    """Search XYZ National University's official knowledge base.

    Searches across all five document collections:
    - CS Department Course Catalog (12 courses)
    - EE Department Course Catalog (8 courses)
    - BBA Department Course Catalog (7 courses)
    - University Academic Policies (grading, fees, attendance, calendar)
    - Faculty Directory (names, emails, offices, specializations)

    Returns a list of the top-k most relevant document chunks, each with
    'content' and 'metadata' (source file, department, doc_type).
    Returns an empty list if the knowledge base has not been ingested yet.
    """
    try:
        vs = get_vectorstore()
        results = vs.similarity_search(query, k=k)
        return [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in results
        ]
    except Exception as exc:
        return [{"content": f"Knowledge base error: {exc}", "metadata": {}}]


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 — Web Search Fallback
# ─────────────────────────────────────────────────────────────────────────────
class WebSearchInput(BaseModel):
    query: str = Field(
        description="Search query to send to the web. Used when the university "
                    "knowledge base does not contain the requested information."
    )
    max_results: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum number of web results to return (default 3).",
    )


@tool(args_schema=WebSearchInput)
def search_web(query: str, max_results: int = 3) -> list[str]:
    """Search the web for information not found in the university knowledge base.

    Uses DuckDuckGo to retrieve current web results. Called as a fallback when
    all retrieved knowledge-base documents are graded as irrelevant.

    Returns a list of text snippets from web search results.
    If the search fails, returns a list with a single error message.
    """
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                snippet = f"{r.get('title', '')}: {r.get('body', '')}"
                results.append(snippet)
        return results if results else ["No web results found for this query."]
    except Exception as exc:
        return [f"Web search error: {exc}"]
