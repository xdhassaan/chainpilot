"""
demo.py - Full SCDRA Capstone Demo Runner

Runs all 5 labs in sequence with clear banners.
Press Enter between each lab to continue.

Usage:
    python demo.py
"""

import os
import sys
import subprocess


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def banner(title: str, lab: str = "") -> None:
    line = "=" * 60
    print(f"\n{line}")
    if lab:
        print(f"  {lab}")
    print(f"  {title}")
    print(f"{line}\n")


def pause(msg: str = "Press Enter to continue to the next lab...") -> None:
    print(f"\n{'─' * 60}")
    input(f"  {msg}")
    print()


def run_script(script_name: str) -> None:
    """Run a Python script in the project directory, streaming output."""
    script_path = os.path.join(BASE_DIR, script_name)
    result = subprocess.run(
        [sys.executable, "-X", "utf8", script_path],
        cwd=BASE_DIR,
        # Filter out sentence-transformers loading noise
        env={**os.environ, "TRANSFORMERS_VERBOSITY": "error"},
    )
    if result.returncode != 0:
        print(f"\n[!] {script_name} exited with code {result.returncode}")


def show_file_summary(filepath: str, max_lines: int = 30) -> None:
    """Print the first N lines of a file."""
    full_path = os.path.join(BASE_DIR, filepath)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print(f"--- {filepath} (first {min(max_lines, len(lines))} of {len(lines)} lines) ---")
        for line in lines[:max_lines]:
            print(line, end="")
        if len(lines) > max_lines:
            print(f"\n  ... ({len(lines) - max_lines} more lines — open file for full content)")
    except FileNotFoundError:
        print(f"[!] File not found: {filepath}")


# ═══════════════════════════════════════════════════════════════════════
#  LAB 1 — Problem Framing & Agentic Architecture
# ═══════════════════════════════════════════════════════════════════════

def demo_lab1() -> None:
    banner("Problem Framing & Agentic Architecture", "LAB 1")
    print("Deliverables: PRD.md, Architecture_Diagram.png")
    print()

    print(">> PRD.md — Problem Statement & Tool Inventory\n")
    show_file_summary("PRD.md", max_lines=40)

    print(f"\n>> Architecture_Diagram.png")
    png_path = os.path.join(BASE_DIR, "Architecture_Diagram.png")
    if os.path.exists(png_path):
        size_kb = os.path.getsize(png_path) // 1024
        print(f"   File exists: {png_path} ({size_kb} KB)")
        print("   Open this file to show the 3-layer architecture diagram:")
        print("   - Perception Layer (6 data sources)")
        print("   - Reasoning Layer  (LangGraph nodes)")
        print("   - Execution Layer  (world-changing actions)")
    else:
        print("   [!] File not found")


# ═══════════════════════════════════════════════════════════════════════
#  LAB 2 — Knowledge Engineering & Domain Grounding
# ═══════════════════════════════════════════════════════════════════════

def demo_lab2() -> None:
    banner("Knowledge Engineering & Domain Grounding", "LAB 2")
    print("Deliverables: ingest_data.py, retrieval_test.md, grounding_justification.txt")
    print()
    print(">> Running ingest_data.py — RAG pipeline (clean → chunk → embed → index)\n")
    run_script("ingest_data.py")

    print("\n>> retrieval_test.md — 3 test queries (including metadata-filtered)\n")
    show_file_summary("retrieval_test.md", max_lines=35)

    print("\n>> grounding_justification.txt — Why RAG over pre-trained LLM\n")
    show_file_summary("grounding_justification.txt", max_lines=20)


# ═══════════════════════════════════════════════════════════════════════
#  LAB 3 — The Reasoning Loop (ReAct with LangGraph)
# ═══════════════════════════════════════════════════════════════════════

def demo_lab3() -> None:
    banner("The Reasoning Loop — ReAct Agent (LangGraph)", "LAB 3")
    print("Deliverables: tools.py (10 tools), graph.py (StateGraph)")
    print()
    print(">> Running graph.py — single-agent ReAct loop\n")
    print("   Watch for:")
    print("   [AI] Tool calls: -> agent deciding which tools to use")
    print("   [Tool]:          -> tool results flowing back")
    print("   [AI]:            -> final synthesized response\n")
    run_script("graph.py")


# ═══════════════════════════════════════════════════════════════════════
#  LAB 4 — Multi-Agent Orchestration
# ═══════════════════════════════════════════════════════════════════════

def demo_lab4() -> None:
    banner("Multi-Agent Orchestration — Researcher / Analyst", "LAB 4")
    print("Deliverables: multi_agent_graph.py, agent_personas.md, collaboration_trace.log")
    print()
    print(">> Running multi_agent_graph.py — Researcher -> Analyst handoff\n")
    print("   Watch for:")
    print("   [RESEARCHER ...]  -> data gathering with read-only tools only")
    print("   [RESEARCHER -> HANDOFF] -> handoff signal detected by router")
    print("   [ANALYST ...]     -> plan drafting + action tools\n")
    run_script("multi_agent_graph.py")

    print("\n>> agent_personas.md — Role definitions and tool restrictions\n")
    show_file_summary("agent_personas.md", max_lines=25)


# ═══════════════════════════════════════════════════════════════════════
#  LAB 5a — Persistent Memory (SqliteSaver)
# ═══════════════════════════════════════════════════════════════════════

def demo_lab5a() -> None:
    banner("State Management — Persistent Memory (SqliteSaver)", "LAB 5 / Task 1")
    print("Deliverables: persistence_test.py, checkpoint_db.sqlite")
    print()
    print(">> Running persistence_test.py — two-turn session memory proof\n")
    print("   Watch for:")
    print("   Turn 1: agent answers question about alternative suppliers")
    print("   Turn 2: agent correctly references Turn 1 context ('the ones you identified')")
    print("   Summary: message count increases across turns, proving checkpoint persistence\n")
    run_script("persistence_test.py")

    db_path = os.path.join(BASE_DIR, "checkpoint_db.sqlite")
    if os.path.exists(db_path):
        size_kb = os.path.getsize(db_path) // 1024
        print(f"\n>> checkpoint_db.sqlite exists: {db_path} ({size_kb} KB)")
        print("   This SQLite file stores the full agent state across sessions.")
    else:
        print("\n[!] checkpoint_db.sqlite not found — run persistence_test.py first")


# ═══════════════════════════════════════════════════════════════════════
#  LAB 5b — Human-in-the-Loop (interrupt_before + state editing)
# ═══════════════════════════════════════════════════════════════════════

def demo_lab5b() -> None:
    banner("Human-in-the-Loop — Safety Breakpoints & State Editing", "LAB 5 / Tasks 2 & 3")
    print("Deliverable: approval_logic.py")
    print()
    print(">> Running approval_logic.py — interrupt_before=['tools']\n")
    print("   Watch for:")
    print("   [!] SAFETY BREAKPOINT  -> graph paused before tool execution")
    print("   [WORLD-CHANGING]       -> flagged tool requiring human review")
    print("   [read-only]            -> auto-approved without pause")
    print("   [Human edited]         -> update_state() injects human edits")
    print("   [Human] Edits applied  -> graph resumes with modified action\n")
    run_script("approval_logic.py")


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  SCDRA Capstone Demo — AI407 Labs 1–5")
    print("  Supply Chain Disruption Response Agent")
    print("=" * 60)
    print("\nThis script demonstrates all 5 labs in sequence.")
    print("Press Enter between labs to proceed.")

    # ── Lab 1 ──
    pause("Press Enter to start Lab 1: Problem Framing...")
    demo_lab1()

    # ── Lab 2 ──
    pause("Press Enter for Lab 2: Knowledge Engineering...")
    demo_lab2()

    # ── Lab 3 ──
    pause("Press Enter for Lab 3: ReAct Reasoning Loop...")
    demo_lab3()

    # ── Lab 4 ──
    pause("Press Enter for Lab 4: Multi-Agent Orchestration...")
    demo_lab4()

    # ── Lab 5a ──
    pause("Press Enter for Lab 5 (Task 1): Persistent Memory...")
    demo_lab5a()

    # ── Lab 5b ──
    pause("Press Enter for Lab 5 (Tasks 2&3): Human-in-the-Loop...")
    demo_lab5b()

    # ── Done ──
    banner("All labs demonstrated successfully!")
    print("Deliverables summary:")
    deliverables = [
        ("Lab 1", ["PRD.md", "Architecture_Diagram.png"]),
        ("Lab 2", ["ingest_data.py", "retrieval_test.md", "grounding_justification.txt"]),
        ("Lab 3", ["tools.py", "graph.py"]),
        ("Lab 4", ["multi_agent_graph.py", "agent_personas.md", "collaboration_trace.log"]),
        ("Lab 5", ["persistence_test.py", "approval_logic.py", "checkpoint_db.sqlite"]),
    ]
    for lab, files in deliverables:
        for f in files:
            path = os.path.join(BASE_DIR, f)
            exists = "OK" if os.path.exists(path) else "MISSING"
            print(f"  [{exists}] {lab}: {f}")

    print(f"\nGitHub: https://github.com/xdhassaan/capstone-lab")


if __name__ == "__main__":
    main()
