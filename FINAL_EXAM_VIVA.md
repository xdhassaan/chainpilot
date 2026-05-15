# Final Exam Viva Preparation Guide
## AI407L — Spring 2026 | Syed Hassaan Ahmed

---

## Quick Reference: What Was Built

| Part | Topic | Key Files |
|------|-------|-----------|
| A | Feedback collection | `app.py` (Streamlit, existing) |
| A | Logging | `feedback_log.db` (SQLite, existing) |
| A | Analysis script | `analyze.py` (NEW) |
| A | Analysis report | `analysis_report.md` (auto-generated) |
| A | Improvement demo | `improvement_demo.md` (NEW) |
| B | Self-RAG agent | `final_exam/self_rag_agent.py` |
| B | LangGraph graph | `final_exam/graph.py` |
| B | Tool definitions | `final_exam/tools.py` |
| B | Evaluation traces | `final_exam/evaluation_results.md` |
| B | KB documents | `final_exam/data/*.pdf` (5 files) |
| B | Vector store | `final_exam/chroma_db/` (ChromaDB) |

---

## PART A — Drift Monitoring & Feedback Loops

### What Was Already Built

The Streamlit dashboard (`app.py`) has a **Feedback & Drift** page (Page 8) with:
- Thumbs up (score=+1) / thumbs down (score=-1) buttons after each agent response
- SQLite `feedback_log.db` — stores every interaction with fields: `id, timestamp, thread_id, user_input, agent_response, feedback_score, optional_comment`

The DB already has **12 real interactions** including 3 negative, 8 positive, 1 neutral.

---

### `analyze.py` — How It Works

**Three things it does:**
1. `SELECT COUNT(*) FROM feedback` → total responses
2. `SELECT COUNT(*) FROM feedback WHERE feedback_score = -1` → negative count
3. `SELECT user_input, agent_response FROM feedback WHERE feedback_score = -1 ORDER BY timestamp DESC LIMIT 3` → top 3 failed queries

**Output:**
- Prints stats to console
- Writes `analysis_report.md` with stats table + top 3 failures table

**Key line:** `feedback_score = -1` is the bad rating. Score values: +1 (good), 0 (neutral), -1 (bad).

**Run it:** `python analyze.py`

---

### Expected Viva Questions — Part A

**Q: What format did you use for logging?**
A: SQLite via Python's built-in `sqlite3`. The `feedback_log.db` file has one table `feedback` with 7 columns. SQLite was chosen over JSON/CSV because it supports efficient queries (COUNT, ORDER BY, WHERE) and concurrent writes from the Streamlit app.

**Q: How does the thumbs up/down work in the UI?**
A: In `app.py`, after each agent response in the Single Agent page, `st.button("👍 Good")` and `st.button("👎 Bad")` call `save_feedback()`. That function does:
```python
conn.execute("INSERT INTO feedback (timestamp, thread_id, user_input, agent_response, feedback_score) VALUES (?, ?, ?, ?, ?)", ...)
```
Score +1 for good, -1 for bad.

**Q: What does your improvement demo show?**
A: From `drift_report.md`, the #7 failure was hallucination: agent said TPA-001 runs at 80% capacity / 50M units/year — data NOT in any supplier document. Fix: Added `[NEW] Anti-Hallucination Rules` to the system prompt in `improved_prompt.txt`, requiring ALL claims to come from tool results. Before: fabricated figures. After: agent says "I don't have data for this — would you like alternatives?"

**Q: What is the satisfaction rate and what caused failures?**
A: 12 total interactions, 8 positive, 3 negative → 66.7% satisfaction. Three failure categories (33% each): Hallucination, Incomplete Answer, Tool Error. All three are addressed by the improved system prompt.

**Q: Why analyze.py instead of modifying analyze_feedback.py?**
A: The exam explicitly requires a file named `analyze.py`. The `analyze_feedback.py` script does a different (more complex) task — LLM-based categorization and full drift report. `analyze.py` is a simpler, exam-specific script that counts totals and prints top 3 failures.

---

## PART B — Self-RAG Agent

### What Is Self-RAG?

Standard RAG always retrieves, always trusts retrieved documents, and never checks if the generated answer is grounded. **Self-RAG adds 3 reflection checkpoints:**

1. **Should I retrieve at all?** — Skip retrieval for greetings/general knowledge
2. **Is what I retrieved actually useful?** — Grade each doc; discard irrelevant ones
3. **Is my answer faithful to the evidence?** — Check the response; regenerate if hallucinated

This produces higher-quality, trustworthy answers in academic advisory contexts where fabricated prerequisite info or policy details would mislead students.

---

### LangGraph State

```python
class SelfRAGState(TypedDict):
    query:                str         # student's question
    messages:             list        # conversation history
    needs_retrieval:      bool        # set by decide_retrieval node
    retrieval_reason:     str         # LLM's reasoning for the decision
    retrieved_docs:       list[dict]  # raw top-4 chunks from ChromaDB
    relevant_docs:        list[str]   # filtered: only relevant chunks' text
    web_results:          list[str]   # DuckDuckGo results (if KB fails)
    context:              list[str]   # whichever source won: relevant_docs or web_results
    draft_response:       str         # generated response before hallucination check
    hallucination_detected: bool      # True if checker found unsupported claims
    retry_count:          int         # 0-3, incremented on each hallucinated response
    final_answer:         str         # the verified (or disclaimed) final output
    trace:                list[str]   # decision log appended by each node
```

---

### The 7 Nodes

#### Node 1: `decide_retrieval`
**What it does:** LLM judge — does this query need KB lookup?  
**LLM prompt:** "Answer YES for university-specific queries (courses, policies, faculty, fees). Answer NO for greetings, general knowledge."  
**Output:** Sets `needs_retrieval` (bool) and `retrieval_reason`  
**Why LLM not rule-based?** Rules would miss edge cases like "What does prerequisite mean?" (general) vs. "What is the prerequisite for CS401?" (specific)

#### Node 2: `retrieve_documents`
**What it does:** Calls `search_university_kb.invoke({"query": query, "k": 4})` — ChromaDB cosine similarity search  
**Output:** Sets `retrieved_docs` (list of 4 dicts with `content` and `metadata`)  
**Why top-4?** Balance between coverage (catch relevant chunks) and noise (avoid irrelevant ones that confuse the grader)

#### Node 3: `grade_relevance`
**What it does:** LLM grades each retrieved doc individually: RELEVANT or IRRELEVANT  
**LLM prompt:** "Is this document chunk relevant to answering this specific query? JSON: {relevant: bool, reason: str}"  
**Output:** Sets `relevant_docs` (only the relevant ones) and `context`  
**Key behavior:** If 0/N docs relevant → `context` is empty → routes to `web_search_fallback`

#### Node 4: `web_search_fallback`
**What it does:** Calls `search_web.invoke({"query": query, "max_results": 3})` — DuckDuckGo search  
**Output:** Sets `web_results` and replaces `context` with web results  
**Why DuckDuckGo?** Free, no API key required, privacy-respecting. Tavily is an alternative but requires an API key.

#### Node 5: `generate_response`
**What it does:** LLM generates answer strictly from `context`  
**LLM prompt:** "Answer using ONLY the information in the provided context. Do NOT add, infer, or fabricate anything not explicitly stated."  
**On retry:** Prompt augmented with "RETRY ATTEMPT {n}: Only state what is explicitly written in the context above."  
**Output:** Sets `draft_response`

#### Node 6: `check_hallucination`
**What it does:** LLM verifier — does the response contain claims NOT in the context?  
**LLM prompt:** "Verify EVERY factual claim in the response is supported by the context. JSON: {hallucinated: bool, unsupported_claims: [...], verdict: GROUNDED|HALLUCINATED}"  
**Key behaviors:**
  - `hallucinated=False` → set `final_answer = draft_response`, route to END
  - `hallucinated=True, retry_count < 3` → increment `retry_count`, route back to `generate_response`
  - `hallucinated=True, retry_count >= 3` → attach disclaimer to response, route to END

#### Node 7: `direct_answer`
**What it does:** LLM answers directly without any retrieved context  
**When used:** Only when `decide_retrieval` returns `needs_retrieval=False`  
**Output:** Sets `final_answer` directly, routes to END

---

### The 3 Routing Functions

```python
def route_after_decision(state):
    # Called after decide_retrieval
    if state["needs_retrieval"]:
        return "retrieve_documents"
    return "direct_answer"

def route_after_grading(state):
    # Called after grade_relevance
    if state["relevant_docs"]:    # non-empty list
        return "generate_response"
    return "web_search_fallback"

def route_after_hallucination(state):
    # Called after check_hallucination
    if not state["hallucination_detected"]:
        return END
    if state["retry_count"] < MAX_RETRIES:   # MAX_RETRIES = 3
        return "generate_response"            # loop back for retry
    return END                                # disclaimer already attached
```

---

### `tools.py` — The @tool Decorators

The exam requires tools defined with `@tool` and Pydantic validation:

```python
class KBSearchInput(BaseModel):
    query: str = Field(description="...")
    k: int = Field(default=4, ge=1, le=10, description="...")

@tool(args_schema=KBSearchInput)
def search_university_kb(query: str, k: int = 4) -> list[dict]:
    """Search XYZ National University's official knowledge base..."""
    vs = get_vectorstore()   # lazy-loads ChromaDB
    results = vs.similarity_search(query, k=k)
    return [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]
```

**Why @tool with Pydantic?** The `@tool` decorator makes the function a LangChain `BaseTool` object (inspectable, serializable, bindable to LLM). Pydantic validates inputs before execution — prevents invalid `k` values (e.g., negative) from reaching ChromaDB.

**Important:** These tools are called by graph nodes directly via `.invoke()`, NOT via LLM tool-calling. The graph controls the flow; the tools encapsulate the side effects (DB lookup, web request).

---

### Knowledge Base Setup

**Chunking strategy:**
- `RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)`
- Separators: `["\n\n", "\n", ". ", " ", ""]` — paragraph breaks first, then sentence, then word
- This keeps course descriptions together (a 3-line course entry fits in 600 chars)
- The 100-char overlap ensures context isn't lost at chunk boundaries

**Metadata per chunk:**
```python
{"source": "CS_Department_Catalog.pdf", "department": "Computer Science", "doc_type": "course_catalog"}
```

**Vector store:** ChromaDB with `all-MiniLM-L6-v2` embeddings (384-dimensional, fast, good semantic quality)
**Collection name:** `university_catalog`
**Total chunks:** 30 (from 5 PDFs, avg ~6 chunks each)

**Run ingestion:** `python ingest.py` — clears and rebuilds `chroma_db/`

---

### Test Case Analysis

| TC | Scenario | Decision Path | Key Evidence |
|----|----------|---------------|-------------|
| TC1 | Greeting | DECISION(NO) -> DIRECT ANSWER | LLM reason: "greeting, no KB needed" |
| TC2 | CS401 prerequisites | DECISION(YES) -> RETRIEVE -> GRADE(1/4) -> GENERATE -> CHECK(GROUNDED) | Answer: "CS301, MATH201, 3 credits" |
| TC3 | TOEFL requirement | DECISION(YES) -> RETRIEVE -> GRADE(0/4) -> WEB SEARCH -> GENERATE -> CHECK(HAL x3) -> DISCLAIMER | Shows web fallback + retry limit |
| TC4 | Ahmed Khan papers | DECISION(YES) -> RETRIEVE -> GRADE(1/4) -> GENERATE -> CHECK(GROUNDED) | LLM declined to fabricate papers |
| TC5 | ML + Power Systems faculty | DECISION(YES) -> RETRIEVE -> GRADE(1/4) -> GENERATE -> CHECK(GROUNDED) | Partial answer, honest about gaps |

**What TC3 proves:**
1. Web fallback works — triggered when 0/4 docs relevant
2. Hallucination check detects unsupported claims ("TOEFL score requirement at XYZ" not in any context)
3. Max retry limit enforced — after 3 attempts, disclaimer appended instead of failing silently

---

### Tricky Viva Questions — Part B

**Q: Why does TC3 fail the hallucination check even after web search?**
A: The DuckDuckGo query for "TOEFL requirements XYZ National University" returns generic TOEFL.com pages (not XYZ-specific data). The `context` then contains web snippets about TOEFL in general. When the LLM generates a response mentioning "XYZ National University" and "TOEFL requirement," the hallucination checker correctly identifies that the phrase "TOEFL requirement at XYZ National University" is NOT in those generic web snippets. This is the hallucination checker working correctly — refusing to let the agent speak with false certainty about XYZ-specific policies it doesn't have.

**Q: What is the difference between `retrieved_docs` and `context`?**
A: `retrieved_docs` = raw results from ChromaDB (all 4 chunks). `context` = the FILTERED source used for generation. If grading finds relevant docs, `context = relevant_docs`. If all docs are irrelevant, `context = web_results`. The `generate_response` node only sees `context` — never the raw retrieved chunks.

**Q: What stops an infinite loop in the hallucination retry?**
A: The `retry_count` field in state. `check_hallucination` increments it each time hallucination is detected. `route_after_hallucination` checks `retry_count < MAX_RETRIES (3)`. After 3 failed attempts, `route_after_hallucination` returns END instead of looping back to `generate_response`.

**Q: Why not use an LLM tool-calling loop instead of this explicit graph?**
A: The Self-RAG architecture requires EXPLICIT routing decisions at each step so that:
1. The retrieval decision and its reasoning are visible in the trace
2. Each document's relevance grade is individually recorded
3. The hallucination check is guaranteed to run (can't be skipped)
4. The retry counter is tracked deterministically
A standard ReAct loop would let the LLM decide what to do at each step, losing the explicit reflection checkpoints that are the core of Self-RAG.

**Q: What is `add_messages` and why is it in the state?**
A: `add_messages` is a LangGraph reducer from `langgraph.graph.message` that APPENDS to the messages list instead of overwriting it. Without it, each node that sets `messages` would overwrite the previous messages, losing conversation history. The `Annotated[list, add_messages]` type annotation tells LangGraph to use this reducer.

**Q: What does `graph = build_graph()` at module level do?**
A: It compiles the StateGraph immediately when `graph.py` is imported. This validates the graph structure (checks all edges connect to defined nodes, catches circular edge errors) at import time rather than at runtime. The compiled graph is then exported so `self_rag_agent.py` just imports and runs it.

**Q: How would you improve TC5 to also find Dr. Umar Farooq for Power Systems?**
A: Increase `k` from 4 to 6 in `search_university_kb`. The relevant Power Systems chunk (Dr. Umar Farooq) exists in the KB but was ranked 5th by cosine similarity. With k=6, it would be retrieved. Alternatively, use metadata filtering: `where={"department": "Electrical Engineering"}` to target the right department catalog directly.

**Q: Explain the `parse_json_response` function.**
A: LLMs sometimes wrap JSON in markdown code blocks (` ```json ... ``` `) or include preamble text. `parse_json_response`:
1. Tries to find a markdown code block and extract its content
2. Falls back to finding the first `{...}` braces using regex
3. Tries `json.loads()` on whatever it found
4. Returns a `default` dict if all parsing fails

This makes LLM JSON outputs robust — a single LLM that slightly deviates from pure JSON won't crash the entire pipeline.

---

### Demo Commands

```bash
# Run the full Self-RAG test suite
cd final_exam && python self_rag_agent.py --test

# Run a single query
cd final_exam && python self_rag_agent.py --query "What are the fees for graduate students?"

# Interactive mode
cd final_exam && python self_rag_agent.py

# Rebuild knowledge base (if needed)
cd final_exam && python ingest.py

# Generate university PDFs (if needed)
cd final_exam && python create_data.py

# Part A: run feedback analysis
python analyze.py
```

---

### Architecture Diagram (ASCII)

```
                    Student Query
                         |
                         v
              +---[decide_retrieval]---+
              |                        |
        needs_retrieval=True     needs_retrieval=False
              |                        |
              v                        v
    [retrieve_documents]        [direct_answer]
     (ChromaDB top-4)                  |
              |                     final_answer
              v                        |
     [grade_relevance]              END
    (grade each doc: Y/N)
       /            \
  has relevant    no relevant
     docs            docs
       |               |
       v               v
[generate_response]  [web_search_fallback]
   (from KB docs)    (DuckDuckGo)
       ^               |
       |               v
       |       [generate_response]
       |         (from web results)
       |               |
       +---------------+
                |
                v
      [check_hallucination]
       /        |        \
   GROUNDED  HALLUC    HALLUC+
              retry<3  retry>=3
       |        |        |
       v        v        v
     END  [generate_response]  END+DISCLAIMER
              (retry)
```

---

## Checklist Before Viva

**Part A deliverables:**
- [ ] `feedback_log.db` — exists with 12 rows
- [ ] `app.py` — Streamlit page with thumbs up/down
- [ ] `analyze.py` — runs and prints stats
- [ ] `analysis_report.md` — generated by analyze.py
- [ ] `improvement_demo.md` — before/after comparison

**Part B deliverables:**
- [ ] `final_exam/data/*.pdf` — all 5 PDFs exist (run `create_data.py` if missing)
- [ ] `final_exam/chroma_db/` — exists (run `ingest.py` if missing)
- [ ] `final_exam/tools.py` — @tool decorators, Pydantic validation
- [ ] `final_exam/graph.py` — compiles without error
- [ ] `final_exam/self_rag_agent.py` — `--test` flag runs all 5 cases
- [ ] `final_exam/evaluation_results.md` — 5 test cases with traces

**Demo commands to practice:**
```bash
python analyze.py                                    # Part A
cd final_exam && python self_rag_agent.py --test    # Part B all 5 tests
cd final_exam && python self_rag_agent.py --query "What are the prerequisites for CS501 Deep Learning?"
```
