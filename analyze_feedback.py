"""
Lab 11 — Drift & Failure Analysis Script for SCDRA.

Analyzes feedback_log.db, categorizes errors using LLM judge,
generates drift_report.md.

Usage:
    python analyze_feedback.py
"""

import json
import os
import sqlite3
import sys

from dotenv import load_dotenv
load_dotenv()

FEEDBACK_DB = os.path.join(os.path.dirname(__file__), "feedback_log.db")
DRIFT_REPORT_PATH = os.path.join(os.path.dirname(__file__), "drift_report.md")


def get_negative_feedback():
    conn = sqlite3.connect(FEEDBACK_DB)
    rows = conn.execute(
        "SELECT id, timestamp, user_input, agent_response, optional_comment "
        "FROM feedback WHERE feedback_score = -1 ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return [{"id": r[0], "timestamp": r[1], "user_input": r[2], "agent_response": r[3], "comment": r[4] or ""} for r in rows]


def get_stats():
    conn = sqlite3.connect(FEEDBACK_DB)
    total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    pos = conn.execute("SELECT COUNT(*) FROM feedback WHERE feedback_score = 1").fetchone()[0]
    neg = conn.execute("SELECT COUNT(*) FROM feedback WHERE feedback_score = -1").fetchone()[0]
    neu = conn.execute("SELECT COUNT(*) FROM feedback WHERE feedback_score = 0").fetchone()[0]
    conn.close()
    return {"total": total, "positive": pos, "negative": neg, "neutral": neu, "satisfaction_rate": round(pos / total * 100, 1) if total else 0}


def categorize_with_llm(entries):
    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
        for e in entries:
            prompt = f"""Categorize this failed agent interaction.
Categories: Hallucination, Tool Error, Wrong Tone, Incomplete Answer, Off-Topic Response, Other

User Input: {e['user_input']}
Agent Response: {e['agent_response'][:500]}
User Comment: {e['comment']}

Respond with ONLY the category name."""
            result = llm.invoke(prompt)
            cat = result.content.strip()
            valid = ["Hallucination", "Tool Error", "Wrong Tone", "Incomplete Answer", "Off-Topic Response", "Other"]
            e["category"] = cat if cat in valid else "Other"
        return entries
    except Exception:
        for e in entries:
            c = (e["comment"] or "").lower()
            if any(w in c for w in ["hallucin", "made up"]):
                e["category"] = "Hallucination"
            elif any(w in c for w in ["tool", "error"]):
                e["category"] = "Tool Error"
            elif any(w in c for w in ["incomplete", "missing"]):
                e["category"] = "Incomplete Answer"
            else:
                e["category"] = "Other"
        return entries


def generate_report(stats, categorized):
    lines = [
        "# Drift Report — Lab 11", "## SCDRA Feedback Analysis", "", "---", "",
        "## 1. Aggregate Statistics", "",
        "| Metric | Value |", "|--------|-------|",
        f"| Total | {stats['total']} |", f"| Positive | {stats['positive']} |",
        f"| Negative | {stats['negative']} |", f"| Neutral | {stats['neutral']} |",
        f"| Satisfaction | {stats['satisfaction_rate']}% |", "", "---", "",
        "## 2. Failure Breakdown", "",
    ]
    if categorized:
        counts = {}
        for e in categorized:
            counts[e["category"]] = counts.get(e["category"], 0) + 1
        lines += ["| Category | Count | % |", "|----------|-------|---|"]
        for cat, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {cat} | {cnt} | {round(cnt/len(categorized)*100,1)}% |")
        lines += ["", "---", "", "## 3. Sample Failures", ""]
        for e in categorized[:5]:
            lines += [f"### #{e['id']} — {e['category']}", f"- Input: {e['user_input'][:200]}", f"- Response: {e['agent_response'][:200]}...", f"- Comment: {e['comment'] or 'N/A'}", ""]
    lines += ["---", "", "## 4. Recommendations", "",
        "1. **Hallucination**: Strengthen grounding — only use tool results.",
        "2. **Tool Error**: Improve tool docstrings and argument examples.",
        "3. **Incomplete**: Require agent to address all parts of multi-part queries.",
        "", "See `improved_prompt.txt` for the revised system prompt."]
    return "\n".join(lines)


def main():
    print("Lab 11 — SCDRA Drift Analysis")
    if not os.path.exists(FEEDBACK_DB):
        print("No feedback DB found.")
        return
    stats = get_stats()
    print(f"Total: {stats['total']}, Positive: {stats['positive']}, Negative: {stats['negative']}")
    neg = get_negative_feedback()
    categorized = categorize_with_llm(neg) if neg else []
    report = generate_report(stats, categorized)
    with open(DRIFT_REPORT_PATH, "w") as f:
        f.write(report)
    print(f"Report saved to {DRIFT_REPORT_PATH}")


if __name__ == "__main__":
    main()
