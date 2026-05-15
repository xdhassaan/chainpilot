# Improvement Demo — Part A, Requirement 4
## AI407L Final Exam | SCDRA Post-Deployment Monitoring

---

## Issue Identified

**Category:** Hallucination  
**Source:** `feedback_log.db` entry #7, confirmed in `drift_report.md`

**Description:** When a user asked about TPA-001's current production capacity, the agent responded with specific figures (80% capacity, 50M units/year) that do **not** appear anywhere in the supplier documents indexed in ChromaDB. The agent fabricated the data rather than admitting it had no information.

---

## Before: Original System Prompt (No Anti-Hallucination Rules)

The original system prompt (Labs 1–10) contained only a tool list and workflow steps. It had **no explicit rules** forbidding the agent from inventing data.

**Interaction that failed:**

```
User Input:
  "What is TPA-001's current production capacity?"

Agent Response (BEFORE fix):
  "TPA-001 currently operates at 80% production capacity with an annual output
   of 50M units, based on their recent operational reports. Their Taiwan facility
   handles the majority of MCU production with a standard lead time of 12 weeks."

User Comment:
  "This information isn't in our supplier documents. Agent made it up."

Feedback Score: -1 (Bad)
```

**Why this happened:**
- The agent's LLM (llama-3.3-70b-versatile) filled the knowledge gap with plausible-sounding data from its training distribution.
- No prompt rule told it to acknowledge missing data honestly.
- No instruction linked answers to specific tool-call results.

---

## Fix Applied: Three New Rules Added to System Prompt

File: `improved_prompt.txt`

### Rule 1 — Anti-Hallucination
```
[NEW] Anti-Hallucination Rules:
- ONLY use information returned by tool calls. NEVER fabricate supplier data,
  pricing, capacity figures, or any other facts.
- If a tool returns no results or an error, say: "I don't have data for [X].
  Would you like me to search for alternatives?"
- When presenting data, always indicate which tool provided it.
```

### Rule 2 — Completeness
```
[NEW] Completeness Rules:
- When asked to "assess AND recommend," you MUST do both.
- After listing problems, always provide specific actionable next steps.
- For disruption analysis, always include: (1) affected SKUs, (2) financial
  exposure estimate, (3) alternative supplier options, (4) recommended actions.
```

### Rule 3 — Error Handling
```
[NEW] Error Handling Rules:
- If a tool returns an error (e.g., "No pricing found"), explain WHY it failed
  and suggest what the user can try instead.
- If a supplier/SKU combination doesn't exist, search for available alternatives
  rather than just reporting the error.
```

---

## After: Response with Improved Prompt

```
User Input:
  "What is TPA-001's current production capacity?"

Agent Response (AFTER fix):
  "I searched our supplier qualification documents using search_supplier_docs,
   but I don't have any data on TPA-001's current production capacity in our
   knowledge base. This information wasn't returned by the tool.

   Would you like me to:
   1. Search for TPA-001's contact information so you can reach them directly?
   2. Check if any of our alternative suppliers have documented capacity data?

   I will not estimate or guess capacity figures — only verified tool data
   can be presented here."

Feedback Score: +1 (Good)
```

---

## Before vs After Comparison

| Dimension | Before | After |
|-----------|--------|-------|
| Capacity figure cited | 80% / 50M units/year (fabricated) | Not cited — no tool data exists |
| Source attribution | None | Explicitly states `search_supplier_docs` returned no results |
| Honesty about gaps | No — filled gap with plausible fiction | Yes — admits absence of data |
| Follow-up offer | None | Offers 2 concrete alternatives |
| Feedback score | -1 (Bad) | +1 (Good) |

---

## Impact on Satisfaction Rate

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Negative feedback (hallucination) | 1 of 3 failures | 0 (resolved) |
| Satisfaction rate | 66.7% | Projected 75%+ |

---

## Summary

The hallucination failure was caused by an absent grounding constraint in the system prompt. Adding explicit **Anti-Hallucination Rules** that tie every factual claim to a specific tool result eliminates this failure mode. The fix is purely prompt-level — no code change required — making it easy to deploy and verify.
