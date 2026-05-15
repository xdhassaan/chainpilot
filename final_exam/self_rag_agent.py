"""
self_rag_agent.py — Part B: Self-RAG University Course Advisory Agent
AI407L Final Exam, Spring 2026

Interactive entry point. Runs the Self-RAG LangGraph pipeline and prints
the decision trace and final answer for each student query.

Usage:
    python self_rag_agent.py                    # interactive REPL
    python self_rag_agent.py --test             # run all 5 predefined test cases
    python self_rag_agent.py --query "..."      # single query mode
"""

import argparse
import os
import sys

from langchain_core.messages import HumanMessage

sys.path.insert(0, os.path.dirname(__file__))
from graph import build_graph

SEPARATOR = "=" * 65


def run_query(graph, query: str, label: str = "") -> dict:
    """Run one query through the Self-RAG graph and print full trace + answer."""
    if label:
        print(f"\n{SEPARATOR}")
        print(f"  TEST CASE: {label}")
        print(SEPARATOR)

    print(f"\nQuery: {query}\n")
    print("[TRACE]")

    initial_state = {
        "query":                query,
        "messages":             [HumanMessage(content=query)],
        "needs_retrieval":      False,
        "retrieval_reason":     "",
        "retrieved_docs":       [],
        "relevant_docs":        [],
        "web_results":          [],
        "context":              [],
        "draft_response":       "",
        "hallucination_detected": False,
        "retry_count":          0,
        "final_answer":         "",
        "trace":                [],
    }

    result = graph.invoke(initial_state, {"recursion_limit": 30})

    print(f"\n[FINAL ANSWER]")
    print("-" * 50)
    answer = result.get("final_answer", "No answer produced.")
    print(answer)
    print("-" * 50)

    trace = result.get("trace", [])
    print(f"\n[DECISION PATH] {' -> '.join(t.split(']')[0].lstrip('[') for t in trace)}")

    return result


def run_test_suite(graph):
    """Run all 5 required test scenarios."""
    test_cases = [
        (
            "TC1 — No Retrieval (Greeting)",
            "Hello! I'm a new student. Can you help me navigate the advisory system?",
        ),
        (
            "TC2 — Retrieval + Relevant Docs",
            "What are the prerequisites for CS401 Machine Learning and how many credit hours is it?",
        ),
        (
            "TC3 — Retrieval + No Relevant Docs -> Web Fallback",
            "What is the TOEFL score requirement for international students applying to XYZ National University?",
        ),
        (
            "TC4 — Hallucination Check (relevant docs + hallucinated extras)",
            "What are Dr. Ahmed Khan's office hours and list 3 of his recently published research papers?",
        ),
        (
            "TC5 — Creative: Multi-department faculty query",
            "I want to study both Machine Learning and Power Systems. "
            "Who are the respective faculty members and what are their email addresses?",
        ),
    ]

    all_results = []
    for label, query in test_cases:
        result = run_query(graph, query, label=label)
        all_results.append({"label": label, "query": query, "result": result})

    print(f"\n{SEPARATOR}")
    print("  ALL TEST CASES COMPLETE")
    print(SEPARATOR)
    return all_results


def interactive_loop(graph):
    print(SEPARATOR)
    print("  XYZ National University — Course Advisory Agent")
    print("  Powered by Self-RAG + LangGraph")
    print("  Type 'quit' or 'exit' to stop")
    print(SEPARATOR)

    while True:
        try:
            query = input("\nStudent Query > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not query:
            continue
        if query.lower() in ("quit", "exit"):
            print("Goodbye!")
            break
        run_query(graph, query)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Self-RAG University Course Advisory Agent")
    parser.add_argument("--test",  action="store_true", help="Run all 5 predefined test cases")
    parser.add_argument("--query", type=str,            help="Run a single query and exit")
    args = parser.parse_args()

    print("Loading Self-RAG graph...")
    graph = build_graph()
    print("Graph ready.\n")

    if args.test:
        run_test_suite(graph)
    elif args.query:
        run_query(graph, args.query)
    else:
        interactive_loop(graph)
