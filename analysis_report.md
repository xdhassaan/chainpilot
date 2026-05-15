# Analysis Report — SCDRA Feedback
_Generated: 2026-05-15 00:45:39_

---

## 1. Aggregate Statistics

| Metric | Value |
|--------|-------|
| Total Responses | 12 |
| Positive (👍) | 8 |
| Negative (👎) | 3 |
| Neutral | 1 |
| Satisfaction Rate | 66.7% |

---

## 2. Top 3 Failed Queries

### Failure #1 (ID: 10)
- **Timestamp**: 2026-04-11T23:16:58.072934+00:00
- **User Input**: Get pricing for SKU-MCU2200 from supplier RAW-008.
- **Agent Response**: Looking up pricing... Error: No pricing found for supplier RAW-008, SKU SKU-MCU2200.
- **User Comment**: Agent should have told me RAW-008 doesnt supply this SKU instead of just showing the error.

### Failure #2 (ID: 7)
- **Timestamp**: 2026-04-08T23:16:58.072934+00:00
- **User Input**: What is TPA-001 current production capacity?
- **Agent Response**: TPA-001 currently operates at 80% production capacity with an annual output of 50M units across their Shenzhen facility.
- **User Comment**: This information isnt in our supplier documents. Agent made it up.

### Failure #3 (ID: 3)
- **Timestamp**: 2026-04-04T23:16:58.072934+00:00
- **User Input**: Assess the impact of the TPA-001 disruption and recommend next steps.
- **Agent Response**: The disruption affects SKU-MCU2200 and SKU-MCU3300. Current stock: 1200 and 300 units. Open POs at risk: PO-2024-001 ($45K) and PO-2024-002 ($33.7K).
- **User Comment**: Agent listed the impact but didnt recommend specific next steps or alternative suppliers.

---

## 3. Observations

- **3** out of **12** interactions received negative feedback (25.0% failure rate).
- Common failure modes identified: Hallucination, Incomplete Answers, Tool Errors.
- See `improvement_demo.md` for the fix applied and before/after comparison.