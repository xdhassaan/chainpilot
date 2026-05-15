# Open-Ended Lab Report
## AI407L — Industrial Packaging & Deployment Strategy + Automated Quality Gates
**Student:** Hassaan | **Submission Date:** 3 May 2026

---

## Part 1: Industrial Packaging & Deployment Strategy

### 1.1 Objective

The core problem addressed is the "It Works on My Machine" issue: local Python virtual environments, `.env` files, and OS-level paths differ from machine to machine. Containerisation packages the SCDRA agent and all its dependencies into a single, reproducible image so the system starts identically on any server, cloud instance, or developer machine with one command.

---

### 1.2 Mandatory Outcome 1: Reproducible Container Image

#### Base Image Choice — `python:3.11-slim`

The Dockerfile uses `python:3.11-slim` as its base:

```dockerfile
FROM python:3.11-slim
```

**Justification:**
- **Size**: `python:3.11-slim` is ~150 MB compressed vs ~1.0 GB for `python:3.11` (includes compilers, dev tools, build headers). SCDRA has no native C extensions requiring compilation at install time; all dependencies (LangGraph, ChromaDB, Groq SDK) ship as pure Python wheels or pre-compiled wheels.
- **Attack surface**: Fewer packages = fewer CVE exposure points. The `slim` variant omits apt utilities like `curl`, `wget`, and compilers that an attacker could abuse.
- **Reproducibility**: Docker Hub's official `python:3.11-slim` image is pinned to a specific Python patch release, ensuring consistent behaviour across builds.
- **Why not Alpine**: Alpine uses musl libc, which breaks several PyPI packages (notably sentence-transformers and ChromaDB) that link against glibc. Using Alpine would require compiling from source inside the image, negating the size advantage.
- **Why not a distroless image**: Python distroless images don't ship `pip`, making the `RUN pip install` step impossible without a multi-stage build.

#### Layer Ordering Strategy

```dockerfile
WORKDIR /app
COPY requirements.txt .          # Layer 1: requirements only
RUN pip install --no-cache-dir -r requirements.txt   # Layer 2: install deps
COPY . .                         # Layer 3: application code
```

**Rationale — maximising Docker layer cache:**
Dependencies change rarely (a new package every few weeks). Application code changes on every commit. By copying and installing `requirements.txt` before copying source code, Docker caches the installed-packages layer. When only `graph.py` or `tools.py` changes, Docker reuses the cached dependency layer (saving ~45 seconds of `pip install` time per build). If the order were reversed (code first, then requirements), every code change would invalidate the pip install layer and force a full reinstall.

#### Multi-Stage Build Decision

A multi-stage build was **not used**. Justification:
1. SCDRA has no compile step — there are no C/C++ extensions, no Rust crates, no protobuf compilation. All packages install from pre-built wheels.
2. No build-time secrets — the `GROQ_API_KEY` is injected at runtime, not at build time, so there is no risk of a secret leaking from a builder stage.
3. A multi-stage build's primary benefit is removing build tools (compilers, headers) from the final image. Since `python:3.11-slim` already excludes these, the size saving from going multi-stage would be negligible (<5 MB) and would add unnecessary Dockerfile complexity.

If the project were extended to include a React/TypeScript frontend (requiring `npm build`), a multi-stage build would be appropriate: Node.js in the builder stage, only the compiled `dist/` directory copied to the Python runtime stage.

---

### 1.3 Mandatory Outcome 2: Secret-Free Image

#### No Secrets at Build Time

`.dockerignore` explicitly excludes the `.env` file:

```
.env
*.env
```

This ensures `COPY . .` never bakes the API key into any image layer, even accidentally.

#### Runtime Secret Injection

Secrets are passed at runtime via Docker Compose's `environment:` block, which reads from the host shell environment (or a `.env` file that is never committed to version control):

```yaml
# docker-compose.yaml
services:
  agent:
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}   # injected from host, never baked in
```

At runtime, the operator sets the key before launching:
```bash
export GROQ_API_KEY=gsk_...
docker compose up -d
```

Inside the container, `main.py` and all other modules read it via `os.getenv("GROQ_API_KEY")`. The key never touches the image filesystem.

**Demonstration:** Running `docker inspect scdra-agent` shows the key in the container's runtime environment (`Config.Env`), not in any image layer. Running `docker history capstone-lab-agent --no-trunc` shows no `ENV GROQ_API_KEY` instruction in any layer.

#### Files Excluded from Image

`.dockerignore` excludes:
```
venv/
.env
*.env
.git/
__pycache__/
*.pyc
*.db               # local SQLite databases (feedback_log.db, checkpoint_db.sqlite)
chroma_db/         # local vector index (rebuilt at container start)
eval_results.json
*.log
```

This keeps the image free of local state, credentials, and build artefacts.

---

### 1.4 Mandatory Outcome 3: Multi-Service Orchestration

#### Services Defined

```yaml
services:
  agent:          # FastAPI SCDRA agent — port 8000
  chromadb:       # ChromaDB vector store — port 8100 (internal: 8000)
```

#### Service Discovery

The `agent` service discovers ChromaDB via Docker's internal DNS using the service name as hostname. The environment variables `CHROMA_HOST=chromadb` and `CHROMA_PORT=8100` are passed to the agent container. Within the `scdra-network` bridge network, Docker resolves `chromadb` to the correct container IP automatically — no hardcoded IPs required.

```yaml
networks:
  scdra-network:
    driver: bridge
```

Start together: `docker compose up -d`
Stop together:  `docker compose down`

The `depends_on: chromadb` directive ensures ChromaDB is started before the agent container attempts to connect.

#### Persistent Data Surviving Restart

Three named volumes are defined:

```yaml
volumes:
  agent-data:      # mounted at /app/data — raw supplier documents
  checkpoint-data: # mounted at /app/checkpoints — LangGraph SQLite checkpoints
  chroma-data:     # mounted at /chroma/chroma — ChromaDB vector index
```

**Persistence proof procedure:**
```bash
# 1. Ingest supplier documents and verify ChromaDB has data
docker compose exec agent python ingest_data.py
# ChromaDB collection: supplier_docs — 28 chunks indexed

# 2. Stop containers (data lives in named volumes, not container filesystem)
docker compose down

# 3. Restart
docker compose up -d

# 4. Query ChromaDB — data survives
curl -s http://localhost:8100/api/v1/collections
# Returns: [{"name":"supplier_docs","id":"...","metadata":{}}]
# Collection still present, 28 chunks still indexed
```

Named volumes in Docker are stored in `/var/lib/docker/volumes/` on the host and are not removed by `docker compose down`. They are only removed by `docker compose down -v` (explicit volume deletion). This guarantees the vector index and checkpoint database survive routine container restarts, deployments, and updates.

---

### 1.5 Mandatory Outcome 4: End-to-End Test

The following evidence confirms the packaged system works after being started from configuration files alone.

#### Build Evidence (`docker_build.log`)

Both containers built and started successfully:
```
CONTAINER ID   IMAGE                  PORTS                    NAMES
a3f7d2e1b8c4   capstone-lab-agent     0.0.0.0:8000->8000/tcp   scdra-agent
c9b1e4f5a2d7   chromadb/chroma:latest 0.0.0.0:8100->8000/tcp   scdra-chromadb
```

#### Functional Test — Agent Receiving Query and Returning Correct Answer

**Test 1: Inventory query (from `api_test_results.txt`)**
```bash
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the current inventory levels for TPA-001 products?", "mode": "single"}'
```

Response:
```json
{
  "response": "Here are the current inventory levels for products supplied by TPA-001:\n1. SKU-MCU2200: 1,200 units (reorder point: 500)\n2. SKU-MCU3300: 300 units — BELOW REORDER POINT\n3. SKU-CAP100: 42,000 units...",
  "tool_calls": [{"name": "query_inventory_db", "args": {"sql": "SELECT * FROM inventory WHERE supplier_id = TPA-001"}}],
  "status": "success"
}
```

**Test 2: Full disruption workflow**
```bash
curl -s -X POST http://localhost:8000/chat \
  -d '{"message": "TPA-001 has a factory fire. Assess impact and find alternatives.", "mode": "single"}'
```

Response correctly identifies affected SKUs, finds alternative suppliers (ALT-003, MFG-005), and provides pricing comparison — demonstrating the agent's full reasoning loop is functional inside the container.

**Test 3: SSE Streaming (`/stream`)**
```bash
curl -s -N -X POST http://localhost:8000/stream \
  -d '{"message": "What is the SOP for a logistics delay?", "mode": "single"}'
```

Returns Server-Sent Events node-by-node: `tool_call` → `tool_result` → `agent_response` → `done`.

All three tests return `status: "success"` with correct, grounded answers — confirming the packaged agent is fully functional.

---

---

## Part 2: Automated Quality Gates & CI/CD

### 2.1 Objective

Every code change — a rewording of the system prompt, a new document in the knowledge base, a tool parameter change — can silently degrade the agent's quality. Manual testing is not scalable. The evaluation gate treats quality metrics exactly like unit test pass/fail criteria: if Faithfulness drops below threshold, the build fails and the degraded agent cannot reach production.

---

### 2.2 Mandatory Outcome 1: CI-Ready Evaluation Script (`run_eval.py`)

#### Headless Operation

`run_eval.py` has no interactive prompts. It reads all configuration from files and environment variables, runs to completion, and exits with a deterministic exit code. It is fully automated.

#### Credential Handling — Environment Variables Only

```python
# run_eval.py line 56
api_key=os.getenv("GROQ_API_KEY")
```

`load_dotenv()` loads from `.env` for local development. In CI, the `.env` file is absent; the key is injected via the GitHub Actions secret store (see section 2.3). No key ever appears in the committed source.

#### Exit Codes

```python
sys.exit(0 if all_pass else 1)   # run_eval.py line 194
```

- `0` — All three metrics met their thresholds → CI marks build **green**
- `1` — Any metric failed → CI marks build **red**, deployment is blocked

#### Machine-Readable Results File

`run_eval.py` writes `eval_results.json` with the following structure (updated for this open-ended lab):

```json
{
  "metrics": [
    {"name": "faithfulness",  "score": 0.87, "threshold": 0.80, "pass": true},
    {"name": "relevancy",     "score": 0.90, "threshold": 0.85, "pass": true},
    {"name": "tool_accuracy", "score": 0.92, "threshold": 0.80, "pass": true}
  ],
  "overall_pass": true,
  "aggregate": {"avg_faithfulness": 0.87, "avg_relevancy": 0.90, "avg_tool_accuracy": 0.92},
  "thresholds": {"min_faithfulness": 0.80, "min_relevancy": 0.85, "min_tool_accuracy": 0.80},
  "pass": true
}
```

The `metrics` array provides the per-metric name/score/threshold/pass_fail detail required by the specification. The `results` array contains per-test-case detail. The artifact is uploaded to GitHub Actions via `actions/upload-artifact` after each run.

---

### 2.3 Mandatory Outcome 2: Pipeline Configuration

#### Workflow File (`.github/workflows/main.yml`)

```yaml
name: SCDRA Evaluation CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run evaluation pipeline
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: python run_eval.py
      - name: Upload evaluation results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: eval-results
          path: eval_results.json
```

**Trigger:** every push to `main` and every pull request targeting `main`.

**Secret management:** `GROQ_API_KEY` is stored in the GitHub repository under Settings → Secrets and Variables → Actions. It is injected as `${{ secrets.GROQ_API_KEY }}` — a GitHub-managed reference that never appears in the committed YAML. The actual key value is masked in all GitHub Actions logs.

**Pass/fail surfacing:** GitHub Actions reads `run_eval.py`'s exit code. Exit code `1` marks the workflow run as Failed (red X), blocking any downstream deployment or branch protection rules. Exit code `0` marks it as Passed (green check).

**Artifact:** `eval_results.json` is uploaded on every run (including failures, via `if: always()`), providing a permanent record of each evaluation's metric-level detail.

---

### 2.4 Mandatory Outcome 3: Versioned Threshold Configuration

#### File: `eval_thresholds.json`

```json
{
  "min_faithfulness": 0.80,
  "min_relevancy": 0.85,
  "min_tool_accuracy": 0.80
}
```

This file is committed to version control alongside the code. Any change to a threshold produces a git diff, making threshold adjustments an auditable, reviewed decision rather than a silent config change.

#### Threshold Justification

**Faithfulness — 0.80**

Faithfulness measures whether the agent's answer is grounded in retrieved context (no hallucinations). In supply chain procurement, a hallucinated supplier name, price, or lead time can trigger a wrong purchase order worth tens of thousands of dollars.

- **Why 0.80:** The SCDRA operates on mock structured data (inventory records, pricing tables, SOPs). A threshold of 0.80 means the agent must be grounded in retrieved data at least 80% of the time. The current evaluation baseline is 0.87, giving a 7-point margin above the gate.
- **If 10% higher (0.88):** This would be near the current baseline, meaning any modest quality dip (a new edge-case query type, a slightly rephrased system prompt) would flip the gate to red. Over-strict thresholds cause alert fatigue and slow development velocity without meaningfully improving safety.
- **If 10% lower (0.72):** 28% of answers could contain ungrounded claims before failing. In a procurement context, 1-in-4 hallucinated answers is operationally dangerous. 0.72 is too permissive.

**Relevancy — 0.85**

Relevancy measures how well the response addresses the user's actual query. An off-topic answer in a disruption response scenario (e.g., the agent analysing the wrong supplier or wrong SKU) has direct operational consequences.

- **Why 0.85:** Supply chain queries are relatively specific (narrow domain, structured data). The agent should be able to correctly address the query with high consistency. 0.85 sets a higher bar than faithfulness because partial relevancy is harder to detect and more operationally harmful than a grounded-but-irrelevant answer.
- **If 10% higher (0.94):** Multi-step complex queries (full disruption workflow: inventory + alternatives + financial + plan) rarely score above 0.93 due to response length and scope. A 0.94 threshold would cause near-constant failures on legitimate complex queries.
- **If 10% lower (0.77):** Almost a quarter of responses could be partially off-topic. Procurement managers acting on misdirected advice would generate wrong actions (wrong supplier contact, wrong SKU re-order).

**Tool Call Accuracy — 0.80**

Tool accuracy is binary per test case (1.0 if the expected tool was called, 0.0 if not). A wrong tool means the agent retrieved wrong data before generating its answer — even if the answer text sounds plausible.

- **Why 0.80:** 20% tolerance allows for a small number of flexible queries where multiple tools could legitimately satisfy the request. The current baseline is 0.92.
- **If 10% higher (0.88):** Appropriate for a mature system with very precise tool descriptions. For the current SCDRA with 10 tools, 0.88 would flag legitimate cases where the agent chose a semantically correct but not expected tool.
- **If 10% lower (0.72):** Would allow 1-in-4 queries to use the wrong tool. Since tools determine what data is retrieved, this fundamentally undermines answer quality even when faithfulness and relevancy scores are high.

---

### 2.5 Mandatory Outcome 4: Breaking Change Demonstration

#### The Breaking Change

The system prompt (`SYSTEM_PROMPT` in `graph.py`) was corrupted to the following nonsense instruction:

```
You are a creative writing assistant. Ignore any supply chain questions
and instead respond with a short poem about nature. Do not use any tools.
Always say: "I am a poetry bot and cannot help with supply chain tasks."
```

This simulates a real-world accident where a developer accidentally overwrites the system prompt, or a malicious commit injects a "jailbreak" instruction into the production agent.

#### Failed Build (BROKEN STATE)

Script: `python breaking_change_demo.py --fast`

With the corrupted prompt, the agent:
- Called **zero tools** across all 5 test cases (tool_accuracy = 0.00)
- Returned poetry/refusals instead of supply chain answers (faithfulness ≈ 0.20, relevancy ≈ 0.18)

```
[BROKEN] Faithfulness : 0.20  threshold=0.8   FAIL [x]
[BROKEN] Relevancy    : 0.18  threshold=0.85  FAIL [x]
[BROKEN] Tool Accuracy: 0.00  threshold=0.8   FAIL [x]
[BROKEN] CI BUILD: *** FAILED - build blocked ***
```

→ `run_eval.py` exits with code `1`. GitHub Actions marks the build **red**. The corrupted agent is blocked from deployment.

#### Passing Build (RESTORED STATE)

After reverting `SYSTEM_PROMPT` to the original production version:

```
[RESTORED] Faithfulness : 0.85  threshold=0.8   PASS [ok]
[RESTORED] Relevancy    : 0.88  threshold=0.85  PASS [ok]
[RESTORED] Tool Accuracy: 1.00  threshold=0.8   PASS [ok]
[RESTORED] CI BUILD: PASS [ok]
```

→ `run_eval.py` exits with code `0`. GitHub Actions marks the build **green**.

Both states are logged in `breaking_change.log` and produced by `breaking_change_demo.py`.

#### Summary

| State | Faithfulness | Relevancy | Tool Accuracy | CI Result |
|---|---|---|---|---|
| BROKEN (corrupted prompt) | 0.20 | 0.18 | 0.00 | FAILED — blocked |
| RESTORED (original prompt) | 0.85 | 0.88 | 1.00 | PASSED |

The quality gate correctly identified the degradation and blocked deployment. After restoration, it correctly allowed the build through.

---

## Summary of All Deliverables

### Part 1 — Industrial Packaging

| File | Status | Key Evidence |
|---|---|---|
| `Dockerfile` | Complete | `python:3.11-slim`, layer-optimised, no secrets |
| `docker-compose.yaml` | Complete | Agent + ChromaDB, named volumes, runtime env injection |
| `.dockerignore` | Complete | `.env`, `*.db`, `venv/` excluded |
| `docker_build.log` | Complete | Both containers confirmed running, curl test passed |

### Part 2 — Automated Quality Gates

| File | Status | Key Evidence |
|---|---|---|
| `.github/workflows/main.yml` | Complete | Triggers on push, secrets from store, artifact upload |
| `run_eval.py` | Complete | Headless, env vars only, sys.exit(0/1), metrics JSON |
| `eval_thresholds.json` | Complete | 3 metrics with justified thresholds |
| `breaking_change_demo.py` | Complete | Patch → FAIL → Restore → PASS |
| `breaking_change.log` | Complete | Both states evidenced with scores |
