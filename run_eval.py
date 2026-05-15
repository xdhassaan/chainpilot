"""
Lab 7 — Evaluation Pipeline (CI-ready) for SCDRA.

Runs the supply chain agent through a test dataset and scores it using
LLM-as-a-Judge (RAGAS-style) on three metrics:
  - Faithfulness:      Does the answer stay true to retrieved context?
  - Answer Relevancy:  How well does the response address the query?
  - Tool Call Accuracy: Did the agent invoke the correct tool(s)?

Exit codes:
  0 — All scores meet thresholds (CI pass)
  1 — One or more scores below threshold (CI fail)

Usage:
    python run_eval.py
"""

import json
import os
import sys
import time

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq

load_dotenv()

from graph import build_graph


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TEST_DATASET_PATH = os.path.join(os.path.dirname(__file__), "test_dataset.json")
THRESHOLD_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "eval_thresholds.json")


def load_test_dataset() -> list[dict]:
    with open(TEST_DATASET_PATH, "r") as f:
        return json.load(f)


def load_thresholds() -> dict:
    with open(THRESHOLD_CONFIG_PATH, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# LLM Judge
# ---------------------------------------------------------------------------
def get_judge_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )


def score_faithfulness(query: str, response: str, reference: str) -> float:
    judge = get_judge_llm()
    prompt = f"""Score the faithfulness of the following response on a scale of 0.0 to 1.0.
Faithfulness means: does the answer stay true to the reference context without hallucinating?

Query: {query}
Reference Context: {reference}
Agent Response: {response}

Respond with ONLY a decimal number between 0.0 and 1.0 (e.g., 0.85).
"""
    result = judge.invoke(prompt)
    try:
        return max(0.0, min(1.0, float(result.content.strip())))
    except ValueError:
        return 0.5


def score_relevancy(query: str, response: str) -> float:
    judge = get_judge_llm()
    prompt = f"""Score the answer relevancy of the following response on a scale of 0.0 to 1.0.
Answer relevancy means: how well does the response address the user's original query?

Query: {query}
Agent Response: {response}

Respond with ONLY a decimal number between 0.0 and 1.0 (e.g., 0.90).
"""
    result = judge.invoke(prompt)
    try:
        return max(0.0, min(1.0, float(result.content.strip())))
    except ValueError:
        return 0.5


def score_tool_accuracy(expected_tool: str, actual_tool_calls: list[str]) -> float:
    return 1.0 if expected_tool in actual_tool_calls else 0.0


# ---------------------------------------------------------------------------
# Run a single test case
# ---------------------------------------------------------------------------
def run_test_case(graph, test_case: dict) -> dict:
    query = test_case["query"]
    expected_tool = test_case["expected_tool"]
    reference = test_case["reference_answer"]

    try:
        result = graph.invoke(
            {"messages": [HumanMessage(content=query)]},
            {"recursion_limit": 25},
        )
    except Exception as e:
        print(f"  ERROR: {e}")
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
    time.sleep(1)
    faithfulness = score_faithfulness(query, final_response, reference)
    time.sleep(1)
    relevancy = score_relevancy(query, final_response)

    return {
        "id": test_case["id"], "category": test_case["category"],
        "query": query, "response": final_response[:300],
        "tool_calls": tool_calls,
        "faithfulness": faithfulness, "relevancy": relevancy, "tool_accuracy": tool_acc,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  Lab 7 — SCDRA Evaluation Pipeline")
    print("=" * 60)

    dataset = load_test_dataset()
    thresholds = load_thresholds()
    print(f"\nTest cases: {len(dataset)}")
    print(f"Thresholds: {json.dumps(thresholds, indent=2)}\n")

    graph = build_graph()
    results = []

    for i, tc in enumerate(dataset):
        print(f"[{i+1}/{len(dataset)}] {tc['category']} — {tc['query'][:60]}...")
        result = run_test_case(graph, tc)
        results.append(result)
        print(f"  F:{result['faithfulness']:.2f} R:{result['relevancy']:.2f} T:{result['tool_accuracy']:.1f} Tools:{result['tool_calls']}")
        time.sleep(2)

    avg_f = sum(r["faithfulness"] for r in results) / len(results)
    avg_r = sum(r["relevancy"] for r in results) / len(results)
    avg_t = sum(r["tool_accuracy"] for r in results) / len(results)

    print(f"\n{'='*60}\n  AGGREGATE SCORES\n{'='*60}")
    print(f"  Faithfulness:      {avg_f:.2f} (>= {thresholds['min_faithfulness']})")
    print(f"  Relevancy:         {avg_r:.2f} (>= {thresholds['min_relevancy']})")
    print(f"  Tool Accuracy:     {avg_t:.2f} (>= {thresholds['min_tool_accuracy']})")

    f_pass = avg_f >= thresholds["min_faithfulness"]
    r_pass = avg_r >= thresholds["min_relevancy"]
    t_pass = avg_t >= thresholds["min_tool_accuracy"]
    all_pass = f_pass and r_pass and t_pass

    print(f"\n  Faithfulness: {'PASS' if f_pass else 'FAIL'}")
    print(f"  Relevancy:    {'PASS' if r_pass else 'FAIL'}")
    print(f"  Tool Acc:     {'PASS' if t_pass else 'FAIL'}")
    print(f"  Overall:      {'PASS' if all_pass else 'FAIL'}")

    output = {
        "metrics": [
            {"name": "faithfulness",  "score": round(avg_f, 2), "threshold": thresholds["min_faithfulness"],  "pass": f_pass},
            {"name": "relevancy",     "score": round(avg_r, 2), "threshold": thresholds["min_relevancy"],     "pass": r_pass},
            {"name": "tool_accuracy", "score": round(avg_t, 2), "threshold": thresholds["min_tool_accuracy"], "pass": t_pass},
        ],
        "overall_pass": all_pass,
        "results": results,
        "aggregate": {"avg_faithfulness": round(avg_f, 2), "avg_relevancy": round(avg_r, 2), "avg_tool_accuracy": round(avg_t, 2)},
        "thresholds": thresholds,
        "pass": all_pass,
    }
    with open("eval_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to eval_results.json")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
