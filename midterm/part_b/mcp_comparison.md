# MCP vs. Alternative Tool Integration Approaches
## AI407L Mid-Term Exam — Part B, Task 3
**Student:** Hassaan | **Course:** AI407L Spring 2026

---

## 1. Why MCP Is Needed in Production Systems

As AI agents move from academic prototypes to production deployments, the way
tools are integrated becomes a critical engineering concern. In early-stage
systems, tools are simply Python functions wired directly into the agent's
runtime. This works for a single developer but breaks down at scale.

Production environments face challenges that direct function calls cannot
address:

- **Heterogeneous runtimes**: A supply chain agent may need to call a pricing
  service written in Java, an inventory database exposed via REST, and a
  document store running in a Docker container — none of them importable as
  Python modules.
- **Team boundaries**: Different teams own different services. Giving every
  agent direct access to every service's internal code creates tight coupling
  and security risks.
- **Dynamic capability discovery**: A production agent should not need a code
  change every time a new tool becomes available. It should be able to query
  what tools exist at runtime.
- **Auditability**: Enterprises require a clear boundary between "what the
  model decided" and "what the system executed", with logs at that boundary.

Model Context Protocol (MCP) addresses all four concerns by standardising the
interface between an AI client (the model) and its tools (external servers)
using a well-defined JSON-RPC protocol over stdio or HTTP/SSE transport. It
decouples the model from the tool implementation, enabling cross-language,
cross-process, and cross-network tool integration without changing agent code.

---

## 2. Comparison: Three Integration Approaches

### 2.1 Direct Tool Invocation (Plain Python Function Calls)

In this pattern — used informally in early prototyping — tools are Python
functions imported and called directly in agent code.

```python
# tools.py
def get_supplier_pricing(supplier_id: str) -> str:
    return f"Price for {supplier_id}: $42.00"

# agent.py
from tools import get_supplier_pricing
result = get_supplier_pricing("TPA-001")
```

**Characteristics:**
- Zero protocol overhead; function calls are microsecond-fast
- No network boundary; tool and agent share the same Python process
- Tool failures crash the agent process
- Adding a new tool requires editing the agent's import list and redeploying
- No capability discovery — agent must know all tools at import time
- No access control — any code in the process can call any function

**Appropriate for:** Single-developer scripts, unit tests, offline demos.

---

### 2.2 LangGraph-Based Orchestration (Stateful Graph with Tool Nodes)

This is the pattern used throughout the SCDRA project (Labs 3–5). Tools are
decorated with `@tool` and bound to an LLM via `.bind_tools()`. LangGraph
manages a `StateGraph` where a `ToolNode` executes tool calls emitted by the
LLM and feeds results back into the message state.

```python
# graph.py (simplified from Lab 3)
from langgraph.prebuilt import ToolNode
from tools import ALL_TOOLS

llm_with_tools = llm.bind_tools(ALL_TOOLS)
tool_node = ToolNode(ALL_TOOLS)

graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.add_conditional_edges("agent", route_agent_output)
graph.add_edge("tools", "agent")
```

**Characteristics:**
- Tools are still Python functions, but structured with Pydantic schemas that
  enforce argument types, preventing the LLM from passing malformed inputs
- State is persistent (SqliteSaver in Lab 5) — conversations survive restarts
- Human-in-the-loop (HITL) is built in via `interrupt_before=["tools"]`
- Multi-agent orchestration allows tool-scoping: the Researcher sees only its
  7 tools; the Analyst sees only its 3 action tools
- All tools still live in the same Python process as the agent
- Deployment still requires all tool dependencies to be installed in the same
  environment
- Tool list is fixed at graph compile time — adding tools requires recompiling

**Appropriate for:** Single-process agents, enterprise workflows needing state
and HITL, teams where all tools are owned by the same service.

---

### 2.3 MCP-Based Modular Exposure (Protocol-Based, Process-Isolated)

MCP introduces a formal client-server boundary. The **MCP Server**
(`mcp_server.py`) registers tools and runs as a completely separate OS process.
The **MCP Client** (`mcp_client.py`) discovers and invokes tools via JSON-RPC
without knowing how they are implemented.

```
[MCP Client]  <--- JSON-RPC over stdio/HTTP --->  [MCP Server]
  - session.initialize()                              - Server.name
  - session.list_tools()                             - @server.list_tools()
  - session.call_tool("analyze_text", {...})         - @server.call_tool()
```

**Characteristics:**
- **Process isolation**: Server crashes do not crash the client; the client
  receives an error response and can retry or fallback
- **Language agnostic**: The server can be written in TypeScript, Go, Rust, or
  any language — the JSON-RPC protocol is the only contract
- **Dynamic discovery**: The client calls `list_tools()` at runtime; adding a
  new tool to the server requires no client code change
- **Versioned contracts**: MCP servers declare a protocol version; clients
  negotiate compatibility during `initialize()`
- **Composability**: One agent can connect to multiple MCP servers
  simultaneously, aggregating tools from different teams or clouds
- **Network transparency**: The same server can be reached over stdio
  (local subprocess), HTTP/SSE (remote service), or WebSocket

**Appropriate for:** Production multi-team systems, cross-language integrations,
microservice architectures, enterprise AI platforms.

---

## 3. Comparison Table

| Dimension | Direct Invocation | LangGraph Orchestration | MCP Protocol |
|-----------|------------------|------------------------|--------------|
| **Coupling** | Tight (import-time) | Medium (bind_tools) | Loose (runtime protocol) |
| **Process boundary** | None (same process) | None (same process) | Yes (separate OS process) |
| **Language requirement** | Python only | Python only | Any language |
| **Tool discovery** | Static (import) | Static (compile-time) | Dynamic (list_tools at runtime) |
| **State management** | Manual | Built-in (StateGraph + SqliteSaver) | Stateless by default (stateful with session) |
| **Fault isolation** | Tool crash = agent crash | Tool crash = agent crash | Tool crash = error response, agent continues |
| **HITL support** | Manual | Built-in (interrupt_before) | Custom (client logic) |
| **Multi-agent** | Manual | Built-in (multi-node graph) | Via client aggregation |
| **Deployment** | Single package | Single package | Independent deployments |
| **Access control** | None (Python scope) | Partial (tool scoping per agent) | Full (server-enforced, network-level) |
| **Auditability** | No boundary log | Graph state log | JSON-RPC message log |
| **Complexity** | Very low | Medium | Higher (protocol + subprocess) |
| **Best for** | Prototypes, tests | Production single-team agents | Production multi-team / microservices |

---

## 4. How MCP Improves Key Properties

### 4.1 Security

Direct function calls and LangGraph tools execute in the agent's process with
the agent's permissions. A malicious or buggy tool can read any environment
variable, write to any file, or exhaust memory — there is no containment.

MCP places tools behind a subprocess boundary. The server can be run under a
restricted OS user account with no access to the agent's secrets. If a tool
needs a database credential, only the server process holds that credential —
the client never sees it. In HTTP-transport mode, the server can additionally
enforce API-key authentication and TLS, providing cryptographic identity
verification for every tool call.

### 4.2 Scalability

A single LangGraph agent running 10 tools is limited by one machine's CPU and
memory. As tool count grows, startup time, memory footprint, and dependency
conflicts all increase.

With MCP, each server is independently deployable and horizontally scalable.
A high-volume tool (e.g., a semantic search service) can be replicated across
10 nodes behind a load balancer, while low-volume tools (e.g., purchase order
update) remain single-instance. The agent client does not change — it still
calls `session.call_tool("search_supplier_docs", {...})`.

### 4.3 System Abstraction

LangGraph tools expose implementation details to the agent: the agent code
imports `from tools import search_supplier_docs` and knows it is a Python
function backed by ChromaDB. If the database migrates to Pinecone, the agent
code changes too.

MCP abstracts this completely. The client only knows the tool name and its
JSON schema. The server can migrate from ChromaDB to Pinecone, from Python to
Rust, from a local file to a remote API — none of these changes are visible to
the client. This is the same principle as service-oriented architecture: program
to the interface, not the implementation.

### 4.4 Separation of Concerns

In a LangGraph project like SCDRA, one developer owns both `tools.py` and
`graph.py`. Changes to tools require the agent developer to update their code.
In a team of 20, this creates a bottleneck.

MCP enforces a hard ownership boundary at the protocol level. The Supply Chain
Data team owns and deploys the MCP server for supplier queries. The AI Platform
team owns the agent client. The contract between them is a JSON schema — the
same schema used in `list_tools()`. Changes on one side do not cascade to the
other, enabling independent release cycles, separate CI/CD pipelines, and
clear accountability.

---

## 5. Summary

| Concern | Winner | Reasoning |
|---------|--------|-----------|
| Simplicity | Direct invocation | No protocol overhead |
| State + HITL | LangGraph | Built-in checkpointing and interrupt |
| Security | MCP | Process isolation, network-level auth |
| Scalability | MCP | Independent horizontal scaling |
| Multi-language | MCP | Protocol-agnostic |
| Team autonomy | MCP | Hard ownership boundary |
| Production readiness | MCP | Designed for enterprise deployment |

For the SCDRA project, LangGraph orchestration is the right choice for the
agent's reasoning loop because state management and HITL are core requirements.
MCP is the right choice for exposing the SCDRA's tools to other services —
for example, allowing a future HR agent or Finance agent to query the same
supplier database without depending on SCDRA's Python codebase.

The two approaches are complementary, not mutually exclusive. A production
SCDRA would use LangGraph internally for orchestration and expose its
capabilities externally via MCP — exactly the separation demonstrated in
Parts A and B of this examination.
