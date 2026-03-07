"""
mcp_server.py - MCP Server for Academic Text Analysis

Mid-Term Exam Part B, Task 1 (10 marks)
AI407L Spring 2026

Implements a Model Context Protocol (MCP) server that exposes three text
analysis tools to any MCP-compatible client. The server communicates over
stdio using JSON-RPC — the standard MCP transport.

MCP Component Breakdown:
  - Model      : The AI / client agent that sends requests (mcp_client.py)
  - Context    : Initialization options passed during the MCP handshake,
                 including the server name and declared capabilities
  - Tools      : Three registered tool functions below
  - Execution  : stdio_server transport + server.run() event loop

Tools exposed:
  1. analyze_text      - Word/sentence statistics and reading-time estimate
  2. extract_keywords  - Top-N meaningful words by frequency
  3. score_readability - Flesch Reading Ease score, grade level, difficulty

All tools are pure Python — no external APIs or LLM calls required.

Usage:
    python mcp_server.py
    (Server waits on stdin for MCP protocol messages from a client)
"""

import asyncio
import json
import math
import re
import string
from collections import Counter

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types


# ============================================================
#  Server Initialisation
# ============================================================

server = Server("text-analysis-server")


# ============================================================
#  Tool Implementation Helpers
# ============================================================

# Common English stop words to exclude from keyword extraction
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "this", "that",
    "these", "those", "it", "its", "their", "they", "we", "our", "you",
    "your", "he", "she", "his", "her", "as", "if", "not", "so", "than",
    "then", "there", "here", "also", "into", "about", "which", "who",
    "what", "when", "where", "how", "all", "each", "both", "more", "most",
    "other", "such", "no", "nor", "only", "same", "very", "just", "after",
    "before", "during", "while", "through", "between", "over", "under",
    "within", "without", "upon", "up", "down", "out", "off", "above",
}


def _tokenize_words(text: str) -> list[str]:
    """Extract lowercase words, stripping punctuation."""
    return [
        w.lower().strip(string.punctuation)
        for w in text.split()
        if w.strip(string.punctuation)
    ]


def _count_syllables(word: str) -> int:
    """Approximate syllable count for a word using vowel-group heuristic."""
    word = word.lower().strip(string.punctuation)
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    # Silent 'e' adjustment
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on . ! ? boundaries."""
    sentences = re.split(r"[.!?]+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


# ============================================================
#  Tool Implementations
# ============================================================

def _analyze_text(text: str) -> dict:
    """Return word/sentence statistics for the provided text."""
    words = _tokenize_words(text)
    sentences = _split_sentences(text)
    unique_words = set(words)

    word_count = len(words)
    unique_word_count = len(unique_words)
    sentence_count = max(len(sentences), 1)
    avg_word_length = (
        round(sum(len(w) for w in words) / word_count, 2) if words else 0.0
    )
    # Average adult reading speed: ~238 words per minute
    reading_time_seconds = round((word_count / 238) * 60)

    return {
        "word_count": word_count,
        "unique_word_count": unique_word_count,
        "sentence_count": sentence_count,
        "avg_word_length": avg_word_length,
        "estimated_reading_time_seconds": reading_time_seconds,
        "lexical_diversity": round(unique_word_count / word_count, 4) if word_count else 0.0,
    }


def _extract_keywords(text: str, top_n: int = 5) -> dict:
    """Return the top-N most frequent non-stop-word tokens."""
    words = _tokenize_words(text)
    meaningful = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    freq = Counter(meaningful)
    top = freq.most_common(top_n)
    return {
        "top_n": top_n,
        "keywords": [{"word": w, "count": c} for w, c in top],
        "total_meaningful_words": len(meaningful),
    }


def _score_readability(text: str) -> dict:
    """
    Compute Flesch Reading Ease score.

    Formula: 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)
    Score interpretation:
      90-100  Very Easy  (5th grade)
      70-90   Easy       (6th grade)
      60-70   Standard   (7th-8th grade)
      50-60   Fairly Difficult (9th-10th grade)
      30-50   Difficult  (college)
      0-30    Very Difficult (college graduate)
    """
    words = _tokenize_words(text)
    sentences = _split_sentences(text)

    word_count = len(words)
    sentence_count = max(len(sentences), 1)
    syllable_count = sum(_count_syllables(w) for w in words)

    if word_count == 0:
        return {"error": "Text contains no words"}

    score = (
        206.835
        - 1.015 * (word_count / sentence_count)
        - 84.6 * (syllable_count / word_count)
    )
    score = round(max(0.0, min(100.0, score)), 2)

    # Map score to grade level and difficulty label
    if score >= 90:
        grade_level = "5th grade"
        difficulty = "Very Easy"
    elif score >= 70:
        grade_level = "6th grade"
        difficulty = "Easy"
    elif score >= 60:
        grade_level = "7th-8th grade"
        difficulty = "Standard"
    elif score >= 50:
        grade_level = "9th-10th grade"
        difficulty = "Fairly Difficult"
    elif score >= 30:
        grade_level = "College"
        difficulty = "Difficult"
    else:
        grade_level = "College Graduate"
        difficulty = "Very Difficult"

    return {
        "flesch_reading_ease": score,
        "grade_level": grade_level,
        "difficulty": difficulty,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "syllable_count": syllable_count,
        "avg_syllables_per_word": round(syllable_count / word_count, 2),
    }


# ============================================================
#  MCP Tool Registry — list_tools handler
# ============================================================

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Advertise the three tools to any connecting MCP client."""
    return [
        types.Tool(
            name="analyze_text",
            description=(
                "Analyze an academic text passage and return basic statistics: "
                "word count, unique word count, sentence count, average word length, "
                "estimated reading time, and lexical diversity."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text passage to analyze.",
                    }
                },
                "required": ["text"],
            },
        ),
        types.Tool(
            name="extract_keywords",
            description=(
                "Extract the top-N most frequent meaningful words from a text passage, "
                "excluding common stop words. Returns each keyword with its occurrence count."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text passage to extract keywords from.",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top keywords to return (default: 5).",
                        "default": 5,
                    },
                },
                "required": ["text"],
            },
        ),
        types.Tool(
            name="score_readability",
            description=(
                "Compute the Flesch Reading Ease score for a text passage. "
                "Returns a score from 0 (hardest) to 100 (easiest), along with "
                "the corresponding grade level and difficulty label."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text passage to score for readability.",
                    }
                },
                "required": ["text"],
            },
        ),
    ]


# ============================================================
#  MCP Tool Execution — call_tool handler
# ============================================================

@server.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[types.TextContent]:
    """Dispatch tool calls and return results as MCP TextContent."""

    if name == "analyze_text":
        text = arguments.get("text", "")
        result = _analyze_text(text)

    elif name == "extract_keywords":
        text = arguments.get("text", "")
        top_n = int(arguments.get("top_n", 5))
        result = _extract_keywords(text, top_n)

    elif name == "score_readability":
        text = arguments.get("text", "")
        result = _score_readability(text)

    else:
        result = {"error": f"Unknown tool: {name}"}

    return [
        types.TextContent(
            type="text",
            text=json.dumps(result, indent=2),
        )
    ]


# ============================================================
#  Entry Point — stdio transport
# ============================================================

async def main():
    """Run the MCP server over stdin/stdout using the stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
