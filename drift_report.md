# Drift Report — Lab 11
## SCDRA Feedback Analysis

---

## 1. Aggregate Statistics

| Metric | Value |
|--------|-------|
| Total | 12 |
| Positive | 8 |
| Negative | 3 |
| Neutral | 1 |
| Satisfaction | 66.7% |

---

## 2. Failure Breakdown

| Category | Count | % |
|----------|-------|---|
| Incomplete Answer | 1 | 33.3% |
| Hallucination | 1 | 33.3% |
| Tool Error | 1 | 33.3% |

---

## 3. Sample Failures

### #3 — Incomplete Answer
- Input: Assess the impact of the TPA-001 disruption and recommend next steps.
- Response: The disruption affects SKU-MCU2200 and SKU-MCU3300. Current stock levels are 1200 and 300 respectively...
- Comment: Agent listed the impact but didn't recommend specific next steps or alternative suppliers.

### #7 — Hallucination
- Input: What is TPA-001's current production capacity?
- Response: TPA-001 currently operates at 80% production capacity with an annual output of 50M units...
- Comment: This information isn't in our supplier documents. Agent made it up.

### #10 — Tool Error
- Input: Get pricing for SKU-MCU2200 from supplier RAW-008.
- Response: I'll look up the pricing for you... Error: No pricing found for supplier RAW-008, SKU SKU-MCU2200.
- Comment: Agent should have told me RAW-008 doesn't supply this SKU instead of just showing the error.

---

## 4. Recommendations

1. **Incomplete Answer (33%)**: Add explicit instructions requiring the agent to provide actionable recommendations after analysis.
2. **Hallucination (33%)**: Strengthen grounding — only answer from tool results, never fabricate data.
3. **Tool Error (33%)**: Improve error handling — when a tool returns an error, explain it clearly and suggest alternatives.

See `improved_prompt.txt` for the revised system prompt.
