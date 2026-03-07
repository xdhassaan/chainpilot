# Technical Report — Supply Chain Disruption Response Agent (SCDRA)
## AI407L Mid-Term Examination | Spring 2026

**Student:** Hassaan
**Course:** AI407L — Agentic AI Systems
**Submission Date:** March 2026

---

## Executive Summary

This report documents the design, implementation, and evaluation of the
**Supply Chain Disruption Response Agent (SCDRA)** — an AI system built to
automate the assessment and response to supplier disruptions in an electronics
manufacturing context.

The project is structured across two examination parts:

**Part A** covers the full agentic pipeline: a RAG-based knowledge foundation
(Lab 2), a single-agent ReAct reasoning loop (Lab 3), multi-agent orchestration
with role-specialised agents (Lab 4), and persistent state management with
human-in-the-loop safety controls (Lab 5).

**Part B** demonstrates the Model Context Protocol (MCP) as an alternative
tool integration standard — a standalone Academic Text Analysis server and
client showing how MCP enables process-isolated, language-agnostic, and
dynamically discoverable tool exposure.

The system reduces the manual disruption response cycle from 4–8 hours to under
30 minutes by automating supplier impact assessment, alternative sourcing, and
stakeholder notification — with human approval gating on all world-changing
actions.

---

## Part A — Agent System

### Lab 2: RAG Pipeline and Knowledge Engineering

#### Problem

A pre-trained LLM has no knowledge of private supplier databases, real-time
inventory levels, or internal audit reports. Without domain grounding, the
agent would hallucinate supplier names, invent compliance statuses, and
generate response plans based on fabricated data. This is unacceptable in
a procurement context where errors have direct financial consequences.

#### Solution: 6-Stage RAG Pipeline (`ingest_data.py`)

The pipeline ingests six simulated internal documents from `data/`:

| Document | Content |
|----------|---------|
| `supplier_profiles.txt` | TPA-001, ECG-002, ALT-003, ALT-004, MFG-005 profiles |
| `logistics_partners.txt` | LOG-006, LOG-007 partner data |
| `raw_materials.txt` | RAW-008, PCK-009 material records |
| `audit_reports.txt` | Q4 2024 QA audit scores and findings |
| `compliance_matrix.txt` | ISO, REACH, RoHS, CMMC compliance per supplier |
| `performance_rankings.txt` | Annual performance scores, Tier 1-4 rankings |

**Stage 1 — Load:** Reads all `.txt` files from the `data/` directory using
Python's standard file I/O.

**Stage 2 — Clean:** Strips ERP system export noise using seven compiled regex
patterns targeting headers (`===== EXPORT =====`), record delimiters
(`<<RECORD>>`), `Generated:` timestamps, and HTML-style tags. This prevents
noise tokens from polluting embeddings.

**Stage 3 — Semantic Chunking:** Splits documents on double-newline boundaries,
preserving each supplier profile as one complete chunk. A procurement analyst
needs the full profile — certifications, lead times, risk notes — in a single
retrieval result. Fragment-level chunking would scatter these across multiple
results, requiring the LLM to piece them together with risk of omission.

**Stage 4 — Metadata Enrichment:** Attaches five metadata tags to each chunk:
- `doc_type`: the source document category (supplier_profile, audit, compliance, etc.)
- `supplier_id`: the extracted supplier identifier (TPA-001, ECG-002, etc.)
- `region`: geographic region extracted from location fields (Asia, Europe, North America)
- `category`: domain category derived from document type
- `priority_level`: urgency tier derived from ranking and audit data

**Stage 5 — Vectorisation:** Embeds each chunk using `all-MiniLM-L6-v2` from
the `sentence-transformers` library. This 22M-parameter model runs locally
(no API key), produces 384-dimensional embeddings, and is well-benchmarked
for semantic similarity retrieval tasks.

**Stage 6 — Indexing:** Persists 28 chunks into a ChromaDB persistent
collection named `supplier_docs` at `./chroma_db/`. ChromaDB was chosen for
its native Python API, local persistence, and built-in metadata filtering.

#### Retrieval Verification (`retrieval_test.md`)

Three queries confirm the pipeline's precision:

1. **Semantic search** for "semiconductor backup supplier" → ALT-003 ranked
   first at cosine distance 0.4206, outranking geographically closer but
   semantically weaker results.

2. **Filtered search** with `where={"category": "audit"}` → restricts results
   to audit findings only, surfacing RAW-008's CONDITIONAL PASS status that
   would otherwise be buried under supplier profiles.

3. **Region filter** with `where={"region": "Europe"}` → returns only ECG-002
   and ALT-004, excluding all Asia-Pacific suppliers. This is critical during
   regional disruptions (e.g., port strikes, tariff changes) where the agent
   must ignore sources in affected geographies.

#### Why RAG over Pre-trained Knowledge (`grounding_justification.txt`)

Four reasons: (1) private data that never appeared in training data, (2) supply
chain data goes stale weekly — RAG can be re-indexed; a fine-tuned model
cannot be updated daily, (3) metadata filtering enables compound queries
impossible with pure semantic search, (4) retrieved chunks serve as an audit
trail — the agent can cite which document each fact came from.

---

### Lab 3: ReAct Reasoning Loop (`graph.py`, `tools.py`)

#### Architecture

The single-agent system implements the **ReAct** (Reason + Act) pattern using
LangGraph's `StateGraph`. The graph has three active components:

**State:**
```python
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```
The `add_messages` reducer appends new messages rather than overwriting,
preserving the full thought-action-observation history across loop iterations.

**Agent Node:** Prepends a system prompt and invokes Groq's
`llama-3.3-70b-versatile` with all 10 tools bound. The LLM reasons over the
message history and either calls one or more tools, or produces a final answer.

**Tool Node:** `ToolNode(ALL_TOOLS)` from `langgraph.prebuilt` executes
whichever tool calls the LLM generated, appends the results as `ToolMessage`
objects, and returns control to the router.

**Conditional Router:**
```python
def route_agent_output(state: State) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END
```
If the last message contains tool calls → route to tools. Otherwise → END.
This loop continues until the LLM produces a plain-text final answer.

#### Tool Design (`tools.py`)

All 10 tools use `@tool` with `args_schema=<PydanticModel>`. Pydantic schemas
enforce argument types at the framework level — the LLM cannot pass a string
where an integer is required. This eliminates a class of runtime errors that
otherwise manifest as hard-to-debug JSON parse failures.

| Tool | Type | Description |
|------|------|-------------|
| `search_supplier_docs` | Read | ChromaDB semantic search over supplier knowledge base |
| `query_inventory_db` | Read | Simulated ERP inventory and PO status |
| `fetch_disruption_alerts` | Read | Active disruption alerts by region/category |
| `load_disruption_history` | Read | Historical disruption response playbooks |
| `get_supplier_pricing` | Read | Lead times, pricing, MOQ by supplier |
| `search_sop_wiki` | Read | Standard Operating Procedure retrieval |
| `calculate_financial_impact` | Calculate | Cost exposure from affected POs |
| `draft_response_plan` | Synthesise | Structured response plan generation |
| `send_notification` | Act | Stakeholder notification (mock) |
| `update_purchase_order` | Act | PO rerouting to backup supplier (mock) |

---

### Lab 4: Multi-Agent Orchestration (`multi_agent_graph.py`, `agent_personas.md`)

#### Motivation

A single agent given a 10-tool repertoire and a complex multi-stage task
suffers from "instruction creep": as the context window fills with tool results,
the agent begins to drift from its initial instructions. Splitting responsibilities
into specialised agents solves this by giving each agent a shorter, more focused
system prompt and a smaller, more relevant tool set.

#### Agent Specialisation

**ResearcherAgent** (7 read-only and calculate tools):
- Goal: gather raw facts; build a complete picture of the disruption
- Constraint: cannot draft plans, send notifications, or update POs
- System prompt explicitly forbids action-taking; closes with a handoff signal

**AnalystAgent** (3 action tools):
- Goal: synthesise Researcher findings into decisions
- Input: the full conversation history including all Researcher tool outputs
- Tools: `draft_response_plan`, `send_notification`, `update_purchase_order`

#### Handoff Protocol

The Researcher ends its final message with:
```
[HANDOFF: Research complete. Passing to Analyst.]
```
The `route_researcher()` conditional edge detects this string and transitions
to the Analyst node. This string-signal approach is robust because it appears
in the LLM's generated text rather than a separate state field — it cannot be
accidentally lost during state serialisation.

#### Graph Topology

Four nodes: `researcher`, `researcher_tools`, `analyst`, `analyst_tools`.
Each tool node is scoped — `researcher_tool_node = ToolNode(RESEARCHER_TOOLS)`
only knows 7 tools. Even if the Researcher LLM tried to call `send_notification`,
the ToolNode would not find it in scope and would return an error, enforcing
the tool boundary at the execution layer.

#### Collaboration Evidence (`collaboration_trace.log`)

A pre-recorded run captured to `collaboration_trace.log` shows the full
execution sequence: Researcher calls 5 data tools, collects results, emits the
handoff signal, and the Analyst calls `draft_response_plan` followed by
`send_notification`. Total messages in final state: 22.

---

### Lab 5: State Management and Human-in-the-Loop

#### Task 1 — Persistent Memory (`persistence_test.py`)

**Problem:** Without persistence, stopping the Python script erases the agent's
full conversation history. A follow-up question in a new script invocation
returns a blank slate — the agent has no memory of the prior turn.

**Solution:** `SqliteSaver` is passed to `graph.compile(checkpointer=...)`.
Every graph step serialises the full State to `checkpoint_db.sqlite` keyed by
`thread_id`. Any subsequent invocation with the same `thread_id` automatically
restores the prior state before running.

**Verification:** Turn 1 asks about alternative MCU chip suppliers for TPA-001.
Turn 2 asks: _"For the alternatives you just identified, what are the pricing
differences?"_ — the pronoun "the alternatives you just identified" is only
resolvable if the agent retains Turn 1's context. The agent answers correctly.
Message count grows from 19 (after Turn 1) to 26 (after Turn 2), confirming
the checkpoint was loaded and extended.

#### Task 2 — Safety Breakpoints (`approval_logic.py`)

The graph is compiled with `interrupt_before=["tools"]`. Before executing any
tool call, LangGraph saves the pending State to SQLite and returns control to
the Python caller. The caller inspects `app.get_state(config)` to retrieve the
pending tool calls, classifies them against `WORLD_CHANGING_TOOLS`, and either
auto-approves (read-only tools) or triggers the human approval gate.

When the gate fires, a `[!] SAFETY BREAKPOINT` banner displays the tool name
and arguments, giving the human operator full visibility before execution.

#### Task 3 — State Editing (`approval_logic.py`)

Beyond approve/cancel, the human can modify the pending action before it
executes. For a `send_notification` call, the operator appends:
```
[EDITED BY HUMAN: Please CC the VP of Operations.]
```
This edit is applied via:
```python
edited_ai_msg = AIMessage(
    content=last_ai_msg.content or "",
    tool_calls=updated_calls,   # human-modified tool call arguments
    id=last_ai_msg.id,          # preserve message identity for deduplication
)
app.update_state(config, {"messages": [edited_ai_msg]})
app.invoke(None, config)        # resume; graph sends the edited version
```
The agent sends the human-edited notification, not the original. The
`[Human edited]` line in the output is the proof.

---

## Part B — MCP Pipeline

### B1 — MCP Server (`midterm/part_b/mcp_server.py`)

#### Domain Choice

The Academic Text Analysis domain was chosen deliberately to be independent of
the supply chain Part A codebase. No imports from `tools.py`, `graph.py`, or
any Part A module appear in Part B. This demonstrates MCP's key property:
servers are self-contained services that can be written, deployed, and owned
independently.

#### MCP Component Mapping

| MCP Concept | Implementation |
|-------------|---------------|
| **Model** | The AI client (`mcp_client.py`) that issues requests |
| **Context** | `server.create_initialization_options()` — server name, version, declared capabilities |
| **Tools** | Three `@server.list_tools()` registered functions |
| **Execution** | `stdio_server` transport + `asyncio.run(server.run(...))` |

#### Tools Implemented

**`analyze_text`** — Computes six statistics over any text passage:
- word count, unique word count, sentence count
- average word length, estimated reading time (at 238 WPM)
- lexical diversity (unique words / total words)

**`extract_keywords`** — Tokenises the text, removes 80+ English stop words,
counts remaining tokens, and returns the top-N most frequent terms with counts.
The `top_n` parameter defaults to 5 but is configurable per call.

**`score_readability`** — Implements the Flesch Reading Ease formula:
```
Score = 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)
```
Syllable count uses a vowel-group heuristic with silent-e adjustment.
The score is clamped to [0, 100] and mapped to a grade level and difficulty
label. Dense academic text typically scores 0–30 (Very Difficult / College
Graduate level), which is expected behaviour.

All tool logic is pure Python — no external APIs, no LLM calls, no network
requests. This makes the server reproducible and testable in isolation.

#### Server Registration Pattern

```python
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(name="analyze_text", description="...", inputSchema={...}), ...]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "analyze_text":
        result = _analyze_text(arguments["text"])
    ...
    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
```

---

### B2 — MCP Client (`midterm/part_b/mcp_client.py`)

The client demonstrates the full five-step MCP lifecycle:

**Step 1 — Connection:** Spawns `mcp_server.py` as a subprocess via
`StdioServerParameters(command=sys.executable, args=[server_script])`.
The `stdio_client` context manager establishes the read/write stream pair.

**Step 2 — Handshake:** `await session.initialize()` sends the MCP
`InitializeRequest` and receives `InitializeResult` containing the server name,
protocol version, and declared capabilities. The protocol version negotiated
is `2025-11-25`, confirming MCP 1.26.0 compliance.

**Step 3 — Tool Discovery:** `await session.list_tools()` returns all three
tools with their names, descriptions, and JSON input schemas. The client prints
these to demonstrate dynamic capability discovery — no tool names are
hardcoded in the client.

**Step 4 — Tool Invocation:** All three tools are called with a sample 101-word
academic paragraph about supply chain resilience.

**Step 5 — Response Handling:** Each `call_tool` response contains a list of
`TextContent` objects. The client parses the JSON payload and pretty-prints
with 4-space indentation, producing readable structured output.

**Sample Output (abridged):**
```json
{
    "word_count": 101,
    "unique_word_count": 88,
    "sentence_count": 5,
    "avg_word_length": 7.31,
    "estimated_reading_time_seconds": 25,
    "lexical_diversity": 0.8713
}
```
```json
{
    "flesch_reading_ease": 0.0,
    "grade_level": "College Graduate",
    "difficulty": "Very Difficult",
    "syllable_count": 249,
    "avg_syllables_per_word": 2.47
}
```
The 0.0 Flesch score is mathematically correct: the raw formula produces -22.24
for text averaging 2.47 syllables/word across 5 sentences, which is clamped to
0. Dense academic prose in the 0–30 range is classified as "Very Difficult /
College Graduate", consistent with published Flesch scale interpretations.

---

### B3 — Technical Comparison

See `midterm/part_b/mcp_comparison.md` for the full analysis. Key conclusions:

- **Direct invocation** is appropriate for prototypes; no protocol overhead
  but no isolation, no dynamic discovery, no cross-language support
- **LangGraph orchestration** is appropriate for production single-team agents
  requiring state, HITL, and multi-agent coordination within one codebase
- **MCP** is appropriate for production multi-team systems requiring process
  isolation, language independence, dynamic tool discovery, and independent
  deployability

The SCDRA system demonstrates both LangGraph (Part A) and MCP (Part B) because
they solve different problems: LangGraph manages the reasoning loop; MCP
exposes capabilities to external consumers.

---

## Technology Choices — Justification

| Choice | Rationale |
|--------|-----------|
| **Groq / llama-3.3-70b-versatile** | Free tier, sub-second inference, no cold starts; 70B parameters sufficient for multi-tool reasoning and structured output |
| **ChromaDB** | Local persistence, no external service dependency, metadata filtering built in, Python-native API |
| **all-MiniLM-L6-v2** | 22M parameters, runs on CPU, well-benchmarked on MTEB semantic similarity tasks, produces 384-dim vectors compatible with ChromaDB |
| **LangGraph over CrewAI / AutoGen** | Explicit graph control enables deterministic routing; SqliteSaver provides production-grade checkpointing; interrupt_before is a first-class HITL primitive |
| **SqliteSaver over MemorySaver** | Survives process restarts; the `.sqlite` file is physical evidence of cross-session recovery; no external database required |
| **MCP over direct function calls** | Process isolation, dynamic discovery, and cross-language compatibility required for production multi-team environments |

---

## Conclusion

The SCDRA system demonstrates a complete production-grade agentic pipeline:
domain knowledge grounded in private data via RAG (Lab 2), autonomous
multi-tool reasoning via ReAct (Lab 3), specialised collaboration via
multi-agent orchestration (Lab 4), and safe real-world execution via persistent
state and human-in-the-loop controls (Lab 5).

Part B extends this foundation by showing how MCP standardises the boundary
between AI clients and their tools — enabling the same capabilities to be
exposed to any MCP-compatible agent regardless of language, runtime, or
deployment topology.

Together, Parts A and B illustrate the two layers of a production AI system
architecture: the **reasoning layer** (LangGraph stateful orchestration) and
the **integration layer** (MCP protocol-based tool exposure).
