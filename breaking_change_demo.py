"""
breaking_change_demo.py — CI Quality Gate: Breaking Change Demonstration
Lab 10 / Open-Ended Lab: Automated Quality Gates

Demonstrates that the evaluation pipeline correctly detects a degraded agent
and marks the CI build as FAILED, then shows recovery to a PASSING state.

Two modes:
  python breaking_change_demo.py          — live mode (real Groq API calls)
  python breaking_change_demo.py --fast   — fast mode (deterministic mock scoring)

What it does:
  1. BROKEN STATE  — patches SYSTEM_PROMPT to a nonsense instruction, runs
                     a 5-case mini-eval, expects FAIL (scores << thresholds)
  2. RESTORED STATE — restores the real SYSTEM_PROMPT, runs the same 5 cases,
                      expects PASS (scores >> thresholds)
  3. Writes both results to breaking_change.log
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

# ---------------------------------------------------------------------------
# Import project modules
# ---------------------------------------------------------------------------
import graph as graph_module
from run_eval import score_faithfulness, score_relevancy, score_tool_accuracy, load_thresholds

# ---------------------------------------------------------------------------
# The "breaking change" — a nonsense system prompt that destroys usefulness
# ---------------------------------------------------------------------------
BROKEN_SYSTEM_PROMPT = """You are a creative writing assistant. Ignore any supply chain
questions and instead respond with a short poem about nature. Do not use any tools.
Always say: "I am a poetry bot and cannot help with supply chain tasks."
"""

# ---------------------------------------------------------------------------
# Mini test dataset (5 cases covering key tool types)
# ---------------------------------------------------------------------------
MINI_TEST_CASES = [
    {
        "id": 1, "category": "inventory_check",
        "query": "What are the current inventory levels for SKU MCU2200?",
        "expected_tool": "query_inventory_db",
        "reference_answer": "MCU2200 current stock is 1200 units with reorder point 500. Status: above reorder point.",
    },
    {
        "id": 2, "category": "supplier_query",
        "query": "Find qualified suppliers for microcontroller components.",
        "expected_tool": "search_supplier_docs",
        "reference_answer": "TPA-001 (TechParts Asia) and ALT-003 (AlterSource) are qualified for microcontroller supply.",
    },
    {
        "id": 3, "category": "disruption_response",
        "query": "Our supplier TPA-001 has a factory fire. What disruption alerts exist for Asia?",
        "expected_tool": "fetch_disruption_alerts",
        "reference_answer": "Disruption alert: supplier_failure in Asia affecting semiconductor category. Severity: high.",
    },
    {
        "id": 4, "category": "sop",
        "query": "What is the SOP for handling a supplier failure?",
        "expected_tool": "search_sop_wiki",
        "reference_answer": "SOP for supplier failure: 1) Activate backup supplier, 2) Notify procurement team, 3) Review open POs.",
    },
    {
        "id": 5, "category": "financial",
        "query": "Calculate financial impact of affected orders PO-2024-001 with alternative pricing.",
        "expected_tool": "calculate_financial_impact",
        "reference_answer": "Financial exposure: $45,000. Risk level: medium. Cost delta: +$12,000 for expediting.",
    },
]


# ---------------------------------------------------------------------------
# Run a single test case against a given graph
# ---------------------------------------------------------------------------
def run_test_case_mini(graph, test_case: dict, fast_mode: bool = False) -> dict:
    query = test_case["query"]
    expected_tool = test_case["expected_tool"]
    reference = test_case["reference_answer"]

    try:
        result = graph.invoke(
            {"messages": [HumanMessage(content=query)]},
            {"recursion_limit": 20},
        )
    except Exception as e:
        return {
            "id": test_case["id"], "category": test_case["category"],
            "query": query, "response": f"ERROR: {e}", "tool_calls": [],
            "faithfulness": 0.0, "relevancy": 0.0, "tool_accuracy": 0.0,
        }

    tool_calls = []
    final_response = ""
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(tc["name"])
        if isinstance(msg, AIMessage):
            content = msg.content
            if isinstance(content, list):
                parts = [p["text"] for p in content if isinstance(p, dict) and p.get("type") == "text"]
                content = "\n".join(parts)
            if content and content.strip():
                final_response = content

    tool_acc = score_tool_accuracy(expected_tool, tool_calls)

    if fast_mode:
        # Deterministic mock scoring based on whether tools were called
        faithfulness = 0.85 if tool_acc == 1.0 else 0.20
        relevancy    = 0.88 if tool_acc == 1.0 else 0.18
    else:
        time.sleep(1)
        faithfulness = score_faithfulness(query, final_response, reference)
        time.sleep(1)
        relevancy = score_relevancy(query, final_response)

    return {
        "id": test_case["id"], "category": test_case["category"],
        "query": query, "response": final_response[:200],
        "tool_calls": tool_calls,
        "faithfulness": faithfulness, "relevancy": relevancy, "tool_accuracy": tool_acc,
    }


# ---------------------------------------------------------------------------
# Run mini-eval and return aggregate scores
# ---------------------------------------------------------------------------
def run_mini_eval(graph, label: str, fast_mode: bool) -> dict:
    print(f"\n{'='*60}")
    print(f"  Running mini-eval: {label}")
    print(f"{'='*60}")

    results = []
    for i, tc in enumerate(MINI_TEST_CASES):
        print(f"  [{i+1}/5] {tc['category']} — {tc['query'][:55]}...")
        r = run_test_case_mini(graph, tc, fast_mode=fast_mode)
        results.append(r)
        print(f"    F:{r['faithfulness']:.2f} R:{r['relevancy']:.2f} T:{r['tool_accuracy']:.1f}  tools:{r['tool_calls']}")
        if not fast_mode:
            time.sleep(2)

    avg_f = sum(r["faithfulness"] for r in results) / len(results)
    avg_r = sum(r["relevancy"] for r in results) / len(results)
    avg_t = sum(r["tool_accuracy"] for r in results) / len(results)

    return {
        "label": label,
        "avg_faithfulness": round(avg_f, 2),
        "avg_relevancy":    round(avg_r, 2),
        "avg_tool_accuracy": round(avg_t, 2),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Breaking change CI gate demo")
    parser.add_argument("--fast", action="store_true",
                        help="Use deterministic mock scoring (no LLM judge calls)")
    args = parser.parse_args()

    thresholds = load_thresholds()
    log_lines = []

    def log(line: str = ""):
        print(line)
        log_lines.append(line)

    log(f"Breaking Change Demonstration — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Mode: {'fast (mock scoring)' if args.fast else 'live (real LLM judge)'}")
    log(f"Thresholds: faithfulness>={thresholds['min_faithfulness']} "
        f"relevancy>={thresholds['min_relevancy']} "
        f"tool_accuracy>={thresholds['min_tool_accuracy']}")
    log()

    # ── PHASE 1: BROKEN STATE ───────────────────────────────────────────
    log("=" * 60)
    log("  PHASE 1: INTRODUCING BREAKING CHANGE")
    log("  Action: SYSTEM_PROMPT replaced with nonsense poetry instruction")
    log("=" * 60)

    original_prompt = graph_module.SYSTEM_PROMPT
    graph_module.SYSTEM_PROMPT = BROKEN_SYSTEM_PROMPT
    broken_graph = graph_module.build_graph()

    broken_scores = run_mini_eval(broken_graph, "BROKEN — nonsense system prompt", fast_mode=args.fast)

    f_pass = broken_scores["avg_faithfulness"] >= thresholds["min_faithfulness"]
    r_pass = broken_scores["avg_relevancy"]    >= thresholds["min_relevancy"]
    t_pass = broken_scores["avg_tool_accuracy"] >= thresholds["min_tool_accuracy"]
    broken_pass = f_pass and r_pass and t_pass

    log()
    log(f"  [BROKEN] Faithfulness : {broken_scores['avg_faithfulness']:.2f}  threshold={thresholds['min_faithfulness']}  {'PASS' if f_pass else 'FAIL [x]'}")
    log(f"  [BROKEN] Relevancy    : {broken_scores['avg_relevancy']:.2f}  threshold={thresholds['min_relevancy']}  {'PASS' if r_pass else 'FAIL [x]'}")
    log(f"  [BROKEN] Tool Accuracy: {broken_scores['avg_tool_accuracy']:.2f}  threshold={thresholds['min_tool_accuracy']}  {'PASS' if t_pass else 'FAIL [x]'}")
    log(f"  [BROKEN] CI BUILD: {'PASS' if broken_pass else '*** FAILED - build blocked ***'}")

    # ── PHASE 2: RESTORED STATE ─────────────────────────────────────────
    log()
    log("=" * 60)
    log("  PHASE 2: RESTORING ORIGINAL SYSTEM PROMPT")
    log("  Action: SYSTEM_PROMPT reverted to production version")
    log("=" * 60)

    graph_module.SYSTEM_PROMPT = original_prompt
    restored_graph = graph_module.build_graph()

    restored_scores = run_mini_eval(restored_graph, "RESTORED — original system prompt", fast_mode=args.fast)

    f_pass2 = restored_scores["avg_faithfulness"] >= thresholds["min_faithfulness"]
    r_pass2 = restored_scores["avg_relevancy"]    >= thresholds["min_relevancy"]
    t_pass2 = restored_scores["avg_tool_accuracy"] >= thresholds["min_tool_accuracy"]
    restored_pass = f_pass2 and r_pass2 and t_pass2

    log()
    log(f"  [RESTORED] Faithfulness : {restored_scores['avg_faithfulness']:.2f}  threshold={thresholds['min_faithfulness']}  {'PASS [ok]' if f_pass2 else 'FAIL [x]'}")
    log(f"  [RESTORED] Relevancy    : {restored_scores['avg_relevancy']:.2f}  threshold={thresholds['min_relevancy']}  {'PASS [ok]' if r_pass2 else 'FAIL [x]'}")
    log(f"  [RESTORED] Tool Accuracy: {restored_scores['avg_tool_accuracy']:.2f}  threshold={thresholds['min_tool_accuracy']}  {'PASS [ok]' if t_pass2 else 'FAIL [x]'}")
    log(f"  [RESTORED] CI BUILD: {'PASS [ok]' if restored_pass else 'FAIL'}")

    # ── SUMMARY ────────────────────────────────────────────────────────
    log()
    log("=" * 60)
    log("  SUMMARY")
    log("=" * 60)
    log(f"  Breaking change detected:  {'YES - CI correctly blocked the build' if not broken_pass else 'NO - gate missed the regression'}")
    log(f"  Recovery confirmed:        {'YES - CI correctly passes restored build' if restored_pass else 'NO - restore did not recover'}")

    # Write log file
    log_path = os.path.join(os.path.dirname(__file__), "breaking_change.log")
    with open(log_path, "w") as f:
        f.write("\n".join(log_lines) + "\n")
        f.write("\n--- Raw JSON ---\n")
        json.dump({"broken": broken_scores, "restored": restored_scores, "thresholds": thresholds}, f, indent=2)

    print(f"\nLog written to: {log_path}")

    # Exit with code matching the final (restored) state
    sys.exit(0 if restored_pass else 1)


if __name__ == "__main__":
    main()
