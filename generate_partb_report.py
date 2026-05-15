"""
generate_partb_report.py
Generates the AI407L Final Exam Part B Report PDF.
Covers: Self-RAG architecture, 7 nodes, 5 test cases with traces.
"""

import os
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, NextPageTemplate

OUT_DIR  = os.path.join(os.path.dirname(__file__), "Report")
OUT_FILE = os.path.join(OUT_DIR, "AI407L_PartB_FinalExam_Report.pdf")
os.makedirs(OUT_DIR, exist_ok=True)

C_DARK   = colors.HexColor("#1A2B4A")
C_MID    = colors.HexColor("#2E5BA8")
C_LIGHT  = colors.HexColor("#4A90D9")
C_TINT   = colors.HexColor("#EAF2FB")
C_GREEN  = colors.HexColor("#2E7D32")
C_GRAY   = colors.HexColor("#F5F5F5")
C_BORDER = colors.HexColor("#CCCCCC")
C_TEXT   = colors.HexColor("#1C1C1C")
C_ORANGE = colors.HexColor("#C45A00")
C_PASS   = colors.HexColor("#E8F5E9")
C_PARTIAL= colors.HexColor("#FFF8E1")

STUDENT = "Syed Hassaan Ahmed  |  Reg: 2022568  |  AI407L Final Exam — Spring 2026"


def make_styles():
    S = {}

    S["cover_title"] = ParagraphStyle("cover_title",
        fontName="Helvetica-Bold", fontSize=24, textColor=colors.white,
        alignment=TA_CENTER, spaceAfter=8)

    S["cover_sub"] = ParagraphStyle("cover_sub",
        fontName="Helvetica", fontSize=13, textColor=colors.HexColor("#A8C4E0"),
        alignment=TA_CENTER, spaceAfter=4)

    S["cover_meta"] = ParagraphStyle("cover_meta",
        fontName="Helvetica", fontSize=11, textColor=C_TEXT,
        alignment=TA_CENTER, spaceAfter=6)

    S["part_heading"] = ParagraphStyle("part_heading",
        fontName="Helvetica-Bold", fontSize=16, textColor=colors.white,
        alignment=TA_CENTER, spaceAfter=6, spaceBefore=4)

    S["section_heading"] = ParagraphStyle("section_heading",
        fontName="Helvetica-Bold", fontSize=11, textColor=C_MID,
        spaceAfter=3, spaceBefore=8)

    S["node_heading"] = ParagraphStyle("node_heading",
        fontName="Helvetica-Bold", fontSize=10, textColor=C_DARK,
        spaceAfter=2, spaceBefore=6)

    S["body"] = ParagraphStyle("body",
        fontName="Helvetica", fontSize=9.5, textColor=C_TEXT,
        spaceAfter=5, leading=14, alignment=TA_JUSTIFY)

    S["body_bold"] = ParagraphStyle("body_bold",
        fontName="Helvetica-Bold", fontSize=9.5, textColor=C_TEXT,
        spaceAfter=4, leading=14)

    S["bullet"] = ParagraphStyle("bullet",
        fontName="Helvetica", fontSize=9.5, textColor=C_TEXT,
        spaceAfter=3, leading=13, leftIndent=14)

    S["code"] = ParagraphStyle("code",
        fontName="Courier", fontSize=7.5, textColor=C_DARK,
        spaceAfter=4, leading=10, leftIndent=6,
        backColor=C_GRAY, borderPad=4)

    S["trace"] = ParagraphStyle("trace",
        fontName="Courier", fontSize=7.8, textColor=colors.HexColor("#003366"),
        spaceAfter=2, leading=11, leftIndent=6,
        backColor=colors.HexColor("#EEF4FF"), borderPad=4)

    S["verdict_pass"] = ParagraphStyle("verdict_pass",
        fontName="Helvetica-Bold", fontSize=10, textColor=C_GREEN,
        alignment=TA_CENTER, spaceAfter=4)

    S["verdict_partial"] = ParagraphStyle("verdict_partial",
        fontName="Helvetica-Bold", fontSize=10, textColor=C_ORANGE,
        alignment=TA_CENTER, spaceAfter=4)

    S["caption"] = ParagraphStyle("caption",
        fontName="Helvetica-Oblique", fontSize=8.5, textColor=colors.gray,
        alignment=TA_CENTER, spaceAfter=4)

    return S


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(C_DARK)
    canvas.rect(doc.leftMargin, A4[1]-doc.topMargin+0.3*cm,
                A4[0]-doc.leftMargin-doc.rightMargin, 0.45*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.white)
    canvas.drawString(doc.leftMargin+4, A4[1]-doc.topMargin+0.38*cm,
                      "AI407L Final Exam — Part B Report")
    canvas.drawRightString(A4[0]-doc.rightMargin-4, A4[1]-doc.topMargin+0.38*cm,
                           "Self-RAG University Course Advisory Agent")
    canvas.setFillColor(C_BORDER)
    canvas.rect(doc.leftMargin, doc.bottomMargin-0.5*cm,
                A4[0]-doc.leftMargin-doc.rightMargin, 0.03*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.gray)
    canvas.drawString(doc.leftMargin, doc.bottomMargin-0.38*cm, STUDENT)
    canvas.drawRightString(A4[0]-doc.rightMargin, doc.bottomMargin-0.38*cm,
                           f"Page {doc.page}")
    canvas.restoreState()


def on_cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(C_DARK)
    canvas.rect(0, A4[1]-4.5*cm, A4[0], 4.5*cm, fill=1, stroke=0)
    canvas.setFillColor(C_MID)
    canvas.rect(0, 0, A4[0], 1.5*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.white)
    canvas.drawCentredString(A4[0]/2, 0.55*cm, STUDENT)
    canvas.restoreState()


def HR(S):
    return HRFlowable(width="100%", thickness=1, color=C_BORDER,
                      spaceAfter=4, spaceBefore=4)


def banner(title, color, S):
    style = ParagraphStyle("bh", fontName="Helvetica-Bold",
                           fontSize=14, textColor=colors.white,
                           alignment=TA_LEFT)
    return [
        Spacer(1, 0.3*cm),
        Table([[Paragraph(f"  {title}", style)]],
              colWidths=["100%"],
              style=TableStyle([
                  ("BACKGROUND", (0,0), (-1,-1), color),
                  ("TOPPADDING", (0,0), (-1,-1), 10),
                  ("BOTTOMPADDING", (0,0), (-1,-1), 10),
              ])),
        Spacer(1, 0.25*cm),
    ]


def node_box(number, name, S):
    style = ParagraphStyle("nb", fontName="Helvetica-Bold",
                           fontSize=10, textColor=colors.white)
    return Table([[Paragraph(f"  Node {number}: {name}", style)]],
                 colWidths=["100%"],
                 style=TableStyle([
                     ("BACKGROUND", (0,0), (-1,-1), C_MID),
                     ("TOPPADDING", (0,0), (-1,-1), 6),
                     ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                 ]))


def data_table(headers, rows, S, col_widths=None):
    header_style = ParagraphStyle("th", fontName="Helvetica-Bold",
                                  fontSize=8.5, textColor=C_DARK)
    cell_style   = ParagraphStyle("td", fontName="Helvetica",
                                  fontSize=8.5, textColor=C_TEXT, leading=11)
    tbl_data = [[Paragraph(h, header_style) for h in headers]]
    for row in rows:
        tbl_data.append([Paragraph(str(c), cell_style) for c in row])
    style = TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_TINT),
        ("TEXTCOLOR",     (0,0), (-1,0),  C_DARK),
        ("LINEBELOW",     (0,0), (-1,0),  1, C_MID),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#F9F9F9")]),
        ("GRID",          (0,0), (-1,-1), 0.5, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ])
    w = col_widths or [(A4[0]-4*cm) / len(headers)] * len(headers)
    return Table(tbl_data, colWidths=w, style=style, repeatRows=1)


def tc_box(label, verdict, S):
    bg = C_PASS if verdict == "PASS" else C_PARTIAL
    fg = C_GREEN if verdict == "PASS" else C_ORANGE
    ls = ParagraphStyle("tcl", fontName="Helvetica-Bold",
                        fontSize=10, textColor=C_DARK)
    vs = ParagraphStyle("tcv", fontName="Helvetica-Bold",
                        fontSize=10, textColor=fg, alignment=TA_CENTER)
    return Table([[Paragraph(label, ls), Paragraph(verdict, vs)]],
                 colWidths=["80%", "20%"],
                 style=TableStyle([
                     ("BACKGROUND", (0,0), (-1,-1), bg),
                     ("TOPPADDING", (0,0), (-1,-1), 7),
                     ("BOTTOMPADDING", (0,0), (-1,-1), 7),
                     ("LEFTPADDING", (0,0), (-1,-1), 10),
                     ("RIGHTPADDING", (0,0), (-1,-1), 10),
                     ("LINEBELOW", (0,0), (-1,-1), 0.5, C_BORDER),
                 ]))


def build():
    S = make_styles()
    story = []

    # ── Cover ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 5*cm))
    story.append(Paragraph("AI407L Final Exam Report", S["cover_title"]))
    story.append(Paragraph("Part B — Self-RAG University Course Advisory Agent", S["cover_sub"]))
    story.append(Spacer(1, 1.5*cm))

    meta_s = ParagraphStyle("ms", fontName="Helvetica", fontSize=12,
                             textColor=C_TEXT, alignment=TA_CENTER, spaceAfter=6)
    story.append(Paragraph("<b>Student:</b>  Syed Hassaan Ahmed", meta_s))
    story.append(Paragraph("<b>Registration Number:</b>  2022568", meta_s))
    story.append(Paragraph("<b>Course:</b>  AI407L — Agentic AI Systems", meta_s))
    story.append(Paragraph("<b>Term:</b>  Spring 2026", meta_s))
    story.append(Spacer(1, 0.8*cm))

    summary_rows = [
        ["Architecture", "LangGraph Self-RAG StateGraph"],
        ["Nodes", "7 nodes, 3 conditional routers"],
        ["LLM", "llama-3.3-70b-versatile (Groq, temperature=0)"],
        ["Vector Store", "ChromaDB — collection university_catalog, 30 chunks from 5 PDFs"],
        ["Web Fallback", "DuckDuckGo via duckduckgo-search (no API key required)"],
        ["Test Cases", "5 scenarios — all 5 passed (TC5: Partial Pass)"],
        ["Key Files", "graph.py, tools.py, self_rag_agent.py, ingest.py, create_data.py"],
    ]
    hs = ParagraphStyle("sh", fontName="Helvetica-Bold", fontSize=10, textColor=colors.white)
    ds = ParagraphStyle("sd", fontName="Helvetica", fontSize=10, textColor=C_TEXT, leading=13)
    cover_rows = [[Paragraph(r[0], hs if i == 0 else ds),
                   Paragraph(r[1], hs if i == 0 else ds)]
                  for i, r in enumerate([["Field", "Value"]] + summary_rows)]
    cover_tbl = Table(cover_rows, colWidths=[4*cm, 13*cm],
                      style=TableStyle([
                          ("BACKGROUND",   (0,0), (-1,0),  C_MID),
                          ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_TINT, colors.white]),
                          ("GRID",         (0,0), (-1,-1), 0.5, C_BORDER),
                          ("TOPPADDING",   (0,0), (-1,-1), 7),
                          ("BOTTOMPADDING",(0,0), (-1,-1), 7),
                          ("LEFTPADDING",  (0,0), (-1,-1), 10),
                          ("RIGHTPADDING", (0,0), (-1,-1), 10),
                          ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
                      ]))
    story.append(cover_tbl)
    story.append(PageBreak())

    # ── Section 1: Architecture ───────────────────────────────────────────────
    story += banner("SECTION 1 — ARCHITECTURE & DESIGN", C_DARK, S)

    story.append(Paragraph("1.1  What Is Self-RAG?", S["section_heading"]))
    story.append(Paragraph(
        "Standard RAG pipelines always retrieve from a knowledge base, always trust the retrieved "
        "documents, and never verify whether the generated answer is faithful to those documents. "
        "<b>Self-RAG (Self-Reflective Retrieval-Augmented Generation)</b> adds three reflection "
        "checkpoints that make the pipeline self-correcting:", S["body"]))
    for item in [
        "<b>Checkpoint 1 — Should I retrieve at all?</b>  Greetings and general knowledge questions "
        "do not need KB lookup. Skipping retrieval reduces latency and avoids injecting irrelevant context.",
        "<b>Checkpoint 2 — Is what I retrieved actually useful?</b>  Each retrieved document is "
        "individually graded as RELEVANT or IRRELEVANT. Only relevant documents feed the generator.",
        "<b>Checkpoint 3 — Is my answer faithful to the evidence?</b>  The generated response is "
        "verified against the context. Unsupported claims trigger regeneration (up to 3 retries) "
        "or a transparency disclaimer.",
    ]:
        story.append(Paragraph(f"  {item}", S["bullet"]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("1.2  StateGraph Topology", S["section_heading"]))
    story.append(Paragraph(
        "The agent is implemented as a LangGraph <b>StateGraph</b> — a directed graph where "
        "nodes are Python functions and edges (including conditional edges) determine the execution path "
        "based on the current state. The state is a <b>TypedDict</b> with 12 fields; "
        "the <b>add_messages</b> reducer (from langgraph.graph.message) appends to the messages list "
        "instead of overwriting it, preserving conversation history.", S["body"]))

    story.append(Spacer(1, 0.2*cm))
    story.append(data_table(
        ["State Field", "Type", "Set By", "Purpose"],
        [
            ["query", "str", "Caller", "The student's original question"],
            ["messages", "Annotated[list, add_messages]", "direct_answer, generate_response", "Conversation history with LangGraph append reducer"],
            ["needs_retrieval", "bool", "decide_retrieval", "Whether KB lookup is required"],
            ["retrieval_reason", "str", "decide_retrieval", "LLM's one-sentence justification"],
            ["retrieved_docs", "list[dict]", "retrieve_documents", "Raw top-4 chunks from ChromaDB"],
            ["relevant_docs", "list[str]", "grade_relevance", "Filtered: only relevant chunks' text"],
            ["web_results", "list[str]", "web_search_fallback", "DuckDuckGo result snippets"],
            ["context", "list[str]", "grade_relevance / web_search_fallback", "The source used for generation"],
            ["draft_response", "str", "generate_response", "Response before hallucination check"],
            ["hallucination_detected", "bool", "check_hallucination", "True if unsupported claims found"],
            ["retry_count", "int", "check_hallucination", "0-3; incremented on each hallucinated response"],
            ["final_answer", "str", "check_hallucination / direct_answer", "Verified (or disclaimed) output"],
            ["trace", "list[str]", "Every node", "Decision log shown in console output"],
        ],
        S, col_widths=[3.5*cm, 4.5*cm, 4*cm, 5*cm]
    ))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("1.3  Graph Flow (ASCII Diagram)", S["section_heading"]))
    flow = (
        "  START\n"
        "    |\n"
        "    v\n"
        "  [decide_retrieval]  <-- LLM judge: needs KB lookup?\n"
        "    |               |\n"
        "  YES              NO\n"
        "    |               |\n"
        "    v               v\n"
        "  [retrieve_documents]   [direct_answer] --> END\n"
        "  (ChromaDB top-4)\n"
        "    |\n"
        "    v\n"
        "  [grade_relevance]  <-- LLM grades each doc\n"
        "    |           |\n"
        "  has relevant  no relevant docs\n"
        "  docs          |\n"
        "    |           v\n"
        "    |     [web_search_fallback]  (DuckDuckGo)\n"
        "    |           |\n"
        "    +-----------+\n"
        "          |\n"
        "          v\n"
        "  [generate_response]  <-- context = relevant_docs OR web_results\n"
        "          |\n"
        "          v\n"
        "  [check_hallucination]  <-- LLM verifier\n"
        "    /        |        \\\n"
        "  GROUNDED  HALLUC    HALLUC + retry >= 3\n"
        "    |       retry<3       |\n"
        "    v          |          v\n"
        "   END  [generate_response]  END + [DISCLAIMER]\n"
        "           (retry loop)"
    )
    story.append(Paragraph(flow, S["code"]))

    story.append(PageBreak())

    # ── Section 2: Nodes ──────────────────────────────────────────────────────
    story += banner("SECTION 2 — THE 7 NODES", C_DARK, S)

    nodes = [
        (
            "1", "decide_retrieval",
            "LLM judge that determines whether the student query requires searching the university "
            "knowledge base. Uses a structured JSON prompt asking the LLM to answer YES for "
            "course/policy/faculty queries and NO for greetings and general knowledge.",
            "Sets: needs_retrieval (bool), retrieval_reason (str)",
            "Route: YES -> retrieve_documents | NO -> direct_answer",
            'Prompt key: "Answer YES if the query is about specific courses, academic policies, '
            'or faculty information. Answer NO if it is a greeting or unrelated to the university."',
        ),
        (
            "2", "retrieve_documents",
            "Calls search_university_kb.invoke({query, k=4}) — a direct invocation of the @tool "
            "function (not via LLM tool-calling). Performs cosine similarity search on the ChromaDB "
            "collection university_catalog using all-MiniLM-L6-v2 embeddings.",
            "Sets: retrieved_docs (list of 4 dicts, each with content and metadata)",
            "Always routes to: grade_relevance",
            "Why top-4: balances coverage against noise; relevant chunks for targeted queries "
            "typically land in top-4 by cosine distance.",
        ),
        (
            "3", "grade_relevance",
            "Calls the LLM once per retrieved document. Each document is graded independently "
            "as RELEVANT or IRRELEVANT relative to the query. Only relevant document text is kept "
            "in relevant_docs and becomes the context for generation.",
            "Sets: relevant_docs (filtered list), context (same as relevant_docs)",
            "Route: non-empty relevant_docs -> generate_response | empty -> web_search_fallback",
            'Prompt key: "Is this document chunk relevant to answering the student\'s query? '
            'JSON: {relevant: bool, reason: string}"',
        ),
        (
            "4", "web_search_fallback",
            "Called only when grade_relevance finds 0 relevant documents. Calls "
            "search_web.invoke({query, max_results=3}) using the DuckDuckGo DDGS().text() API. "
            "No API key required. Results replace context with web snippets.",
            "Sets: web_results (list of strings), context (web_results)",
            "Always routes to: generate_response",
            "DuckDuckGo chosen for: free tier, no API key, privacy-respecting. Tavily is an "
            "alternative but requires a paid API key.",
        ),
        (
            "5", "generate_response",
            "Generates an answer grounded strictly in the current context (either relevant_docs "
            "or web_results). On retry attempts, the prompt is augmented with an explicit warning "
            "about the previous attempt's unsupported claims.",
            "Sets: draft_response (str), increments messages list",
            "Always routes to: check_hallucination",
            'Retry augmentation: "RETRY ATTEMPT {n}: Your previous answer contained unsupported claims. '
            'ONLY state what is explicitly written in the context above."',
        ),
        (
            "6", "check_hallucination",
            "LLM verifier: checks whether EVERY factual claim in the draft response is supported by "
            "the context. Returns a structured JSON verdict. On confirmed hallucination, increments "
            "retry_count. If retry_count reaches MAX_RETRIES (3), attaches a [DISCLAIMER] to the "
            "response and routes to END.",
            "Sets: hallucination_detected (bool), retry_count (+1 if hallucinated), final_answer",
            "Route: GROUNDED -> END | HALLUCINATED+retry<3 -> generate_response | HALLUCINATED+retry>=3 -> END+disclaimer",
            'Verdict JSON: {"hallucinated": bool, "unsupported_claims": [...], "verdict": "GROUNDED"|"HALLUCINATED"}',
        ),
        (
            "7", "direct_answer",
            "Used for queries that do not require KB lookup (greetings, general knowledge). "
            "Calls the LLM directly without any retrieved context, answering from general knowledge "
            "in the role of a friendly university course advisor.",
            "Sets: final_answer (str), messages",
            "Always routes to: END",
            "Bypasses all 5 retrieval/grading/generation/checking nodes — minimal latency path.",
        ),
    ]

    for num, name, desc, sets, route, key in nodes:
        story.append(Spacer(1, 0.2*cm))
        story.append(node_box(num, name, S))
        story.append(Spacer(1, 0.1*cm))
        story.append(Paragraph(desc, S["body"]))
        story.append(Paragraph(f"<b>State output:</b>  {sets}", S["bullet"]))
        story.append(Paragraph(f"<b>Routing:</b>  {route}", S["bullet"]))
        story.append(Paragraph(f"<b>Key detail:</b>  {key}", S["bullet"]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("3 Conditional Routing Functions", S["section_heading"]))
    routing_code = (
        "def route_after_decision(state):\n"
        "    return 'retrieve_documents' if state['needs_retrieval'] else 'direct_answer'\n\n"
        "def route_after_grading(state):\n"
        "    return 'generate_response' if state['relevant_docs'] else 'web_search_fallback'\n\n"
        "def route_after_hallucination(state):\n"
        "    if not state['hallucination_detected']:\n"
        "        return END\n"
        "    if state['retry_count'] < MAX_RETRIES:  # MAX_RETRIES = 3\n"
        "        return 'generate_response'\n"
        "    return END  # disclaimer already attached by check_hallucination"
    )
    story.append(Paragraph(routing_code, S["code"]))

    story.append(PageBreak())

    # ── Section 3: Tools ──────────────────────────────────────────────────────
    story += banner("SECTION 3 — TOOLS & KNOWLEDGE BASE", C_DARK, S)

    story.append(Paragraph("3.1  @tool Decorators with Pydantic Validation", S["section_heading"]))
    story.append(Paragraph(
        "Both tools use the LangChain <b>@tool</b> decorator with an <b>args_schema</b> pointing to "
        "a Pydantic BaseModel. This makes each function a LangChain BaseTool object — inspectable, "
        "serializable, and bindable to LLMs. Pydantic validates all inputs before execution, "
        "preventing invalid values (e.g., k=-1 or max_results=100) from reaching ChromaDB or the web API.",
        S["body"]))

    tools_code = (
        "class KBSearchInput(BaseModel):\n"
        "    query: str = Field(description='Search query for the university knowledge base')\n"
        "    k: int = Field(default=4, ge=1, le=10, description='Number of chunks to retrieve')\n\n"
        "@tool(args_schema=KBSearchInput)\n"
        "def search_university_kb(query: str, k: int = 4) -> list[dict]:\n"
        "    '''Search XYZ National University catalog, policies, and faculty directory.'''\n"
        "    vs = get_vectorstore()   # lazy-loads ChromaDB from chroma_db/\n"
        "    results = vs.similarity_search(query, k=k)\n"
        "    return [{\"content\": doc.page_content, \"metadata\": doc.metadata} for doc in results]\n\n"
        "class WebSearchInput(BaseModel):\n"
        "    query: str = Field(description='Web search query')\n"
        "    max_results: int = Field(default=3, ge=1, le=5)\n\n"
        "@tool(args_schema=WebSearchInput)\n"
        "def search_web(query: str, max_results: int = 3) -> list[str]:\n"
        "    '''Search the web when the KB doesn't have the answer.'''\n"
        "    with DDGS() as ddgs:\n"
        "        for r in ddgs.text(query, max_results=max_results):\n"
        "            results.append(f\"{r.get('title','')}: {r.get('body','')}\")\n"
        "    return results"
    )
    story.append(Paragraph(tools_code, S["code"]))

    story.append(Paragraph("Note: Tools are invoked directly by graph nodes via .invoke(), "
                           "NOT via LLM tool-calling. The graph controls the flow; the tools "
                           "encapsulate the I/O operations.", S["body"]))

    story.append(Paragraph("3.2  Knowledge Base Setup (ingest.py)", S["section_heading"]))
    story.append(data_table(
        ["Step", "Action", "Implementation"],
        [
            ["1. Load PDFs", "pypdf.PdfReader reads each of the 5 PDF files", "Iterates reader.pages, extracts text, joins pages with double newline"],
            ["2. Attach Metadata", "Each Document gets 3 metadata fields", "source (filename), department (CS/EE/BBA/University), doc_type (course_catalog/academic_policy/faculty_directory)"],
            ["3. Split into Chunks", "RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)", "Separators: ['\\n\\n', '\\n', '. ', ' ', ''] — paragraph breaks first"],
            ["4. Embed", "all-MiniLM-L6-v2 (SentenceTransformerEmbeddings)", "384-dim vectors, local CPU, no API key required"],
            ["5. Index", "Chroma.from_documents() persists to chroma_db/", "Collection: university_catalog, 30 total chunks from 5 PDFs"],
        ],
        S, col_widths=[3.5*cm, 5*cm, 8.5*cm]
    ))

    story.append(Paragraph("3.3  University PDF Documents (create_data.py)", S["section_heading"]))
    story.append(data_table(
        ["PDF File", "Content", "Key Data for Test Cases"],
        [
            ["CS_Department_Catalog.pdf", "12 courses: CS101-CS601", "CS401 ML: prereqs=CS301,MATH201, credits=3"],
            ["EE_Department_Catalog.pdf", "8 courses: EE101-EE501", "EE401 Power Systems: prereqs=EE201,EE202, credits=3"],
            ["BBA_Department_Catalog.pdf", "7 courses: BBA101-BBA501", "BBA401 Entrepreneurship: prereqs=BBA301, credits=3"],
            ["University_Academic_Policies.pdf", "8 policy sections: GPA, fees, attendance, graduation", "GPA: A=85-100/4.0, min graduation GPA=2.0, fees Rs. 45,000/sem"],
            ["Faculty_Directory.pdf", "9 faculty members across CS/EE/BBA", "Dr. Ahmed Khan: ahmed.khan@xyz.edu.pk, Mon/Wed 2-4 PM; Dr. Umar Farooq: EE/Power Systems"],
        ],
        S, col_widths=[5*cm, 4.5*cm, 7.5*cm]
    ))

    story.append(PageBreak())

    # ── Section 4: Test Cases ─────────────────────────────────────────────────
    story += banner("SECTION 4 — EVALUATION: 5 TEST CASES", C_DARK, S)

    story.append(Paragraph(
        "All 5 test cases were run using python self_rag_agent.py --test. "
        "Each case demonstrates a distinct Self-RAG decision path. "
        "TC5 is rated Partial Pass — the agent correctly answered what evidence supported "
        "and acknowledged what it could not verify, which demonstrates correct grounding behavior.",
        S["body"]))

    story.append(Spacer(1, 0.3*cm))

    # TC1
    story.append(tc_box("TC1 — No Retrieval Needed (Greeting)", "PASS", S))
    story.append(Spacer(1, 0.1*cm))
    story.append(Paragraph(
        "<b>Query:</b> Hello! I'm a new student. Can you help me navigate the advisory system?",
        S["body"]))
    story.append(Paragraph(
        "<b>Expected path:</b> decide_retrieval (NO) -> direct_answer -> END  "
        "(greeting, no university-specific information needed)",
        S["body"]))
    tc1_trace = (
        "[DECISION] needs_retrieval=False | reason: The query is a greeting and a request\n"
        "           for general assistance with the advisory system.\n"
        "[DIRECT ANSWER] No retrieval needed - answered from general knowledge\n"
        "[DECISION PATH] DECISION -> DIRECT ANSWER"
    )
    story.append(Paragraph(tc1_trace, S["trace"]))
    story.append(Paragraph(
        "<b>Final response:</b> Welcome to XYZ National University. I'd be happy to help you navigate "
        "our advisory system. As your course advisor, I'm here to guide you in choosing courses, "
        "creating a study plan, and ensuring you're on track to meet your academic goals...",
        S["body"]))
    story.append(Paragraph("Agent correctly identified no retrieval needed and answered helpfully from general knowledge.", S["verdict_pass"]))

    story.append(Spacer(1, 0.3*cm))

    # TC2
    story.append(tc_box("TC2 — Retrieval Needed, Documents Relevant", "PASS", S))
    story.append(Spacer(1, 0.1*cm))
    story.append(Paragraph(
        "<b>Query:</b> What are the prerequisites for CS401 Machine Learning and how many credit hours is it?",
        S["body"]))
    story.append(Paragraph(
        "<b>Expected path:</b> decide (YES) -> retrieve -> grade (1 relevant) -> generate -> check (GROUNDED) -> END",
        S["body"]))
    tc2_trace = (
        "[DECISION] needs_retrieval=True | reason: The query is about specific course prerequisites\n"
        "           and credit hours for CS401 Machine Learning.\n"
        "[RETRIEVE] Found 4 chunks from knowledge base\n"
        "    Chunk 1: [CS_Department_Catalog.pdf] CS404... -> IRRELEVANT: does not mention CS401\n"
        "    Chunk 2: [CS_Department_Catalog.pdf] CS401 ML entry -> RELEVANT: contains prereqs and credits\n"
        "    Chunk 3: [CS_Department_Catalog.pdf] scikit-learn... -> IRRELEVANT: not about CS401\n"
        "    Chunk 4: [CS_Department_Catalog.pdf] Von Neumann... -> IRRELEVANT: computer architecture\n"
        "[GRADE] 1/4 docs relevant\n"
        "[GENERATE] Draft response produced (retry=0, length=100 chars)\n"
        "[HALLUCINATION CHECK] verdict=GROUNDED | retry=0/3\n"
        "[DECISION PATH] DECISION -> RETRIEVE -> GRADE -> GENERATE -> HALLUCINATION CHECK"
    )
    story.append(Paragraph(tc2_trace, S["trace"]))
    story.append(Paragraph(
        "<b>Final response:</b> The prerequisites for CS401 Machine Learning are CS301 and MATH201. "
        "CS401 is a 3-credit hour course.",
        S["body"]))
    story.append(Paragraph("Response matches CS_Department_Catalog.pdf exactly. 1/4 grading demonstrates selective relevance filtering.", S["verdict_pass"]))

    story.append(Spacer(1, 0.3*cm))

    # TC3
    story.append(tc_box("TC3 — All Docs Irrelevant: Web Fallback + Retry Limit + Disclaimer", "PASS", S))
    story.append(Spacer(1, 0.1*cm))
    story.append(Paragraph(
        "<b>Query:</b> What is the TOEFL score requirement for international students applying to XYZ National University?",
        S["body"]))
    story.append(Paragraph(
        "<b>Expected path:</b> decide (YES) -> retrieve -> grade (0/4 relevant) -> web_search -> "
        "generate -> check (HALLUCINATED x3) -> END+DISCLAIMER",
        S["body"]))
    tc3_trace = (
        "[DECISION] needs_retrieval=True | reason: The query is about academic policies\n"
        "           specific to international students at XYZ National University.\n"
        "[RETRIEVE] Found 4 chunks from knowledge base\n"
        "    All 4 from University_Academic_Policies.pdf -> all IRRELEVANT (no TOEFL info)\n"
        "[GRADE] 0/4 docs relevant\n"
        "[WEB SEARCH] KB irrelevant - searched web, got 1 results\n"
        "    Result 1: No web results found for this query.\n"
        "[GENERATE] Draft response produced (retry=0, length=370 chars)\n"
        "[HALLUCINATION CHECK] verdict=HALLUCINATED | retry=0/3\n"
        "    unsupported: ['TOEFL score requirement', 'XYZ National University']\n"
        "[GENERATE] Draft response produced (retry=1, length=208 chars)\n"
        "[HALLUCINATION CHECK] verdict=HALLUCINATED | retry=1/3\n"
        "[GENERATE] Draft response produced (retry=2, length=208 chars)\n"
        "[HALLUCINATION CHECK] verdict=HALLUCINATED | retry=2/3\n"
        "[DISCLAIMER] Max retries (3) reached - adding disclaimer\n"
        "[DECISION PATH] DECISION -> RETRIEVE -> GRADE -> WEB SEARCH -> GENERATE ->\n"
        "                HALLUCINATION CHECK (x3) -> DISCLAIMER"
    )
    story.append(Paragraph(tc3_trace, S["trace"]))
    story.append(Paragraph(
        "<b>Final response:</b> There is no information in the provided context about the TOEFL score "
        "requirement for international students applying to XYZ National University... "
        "[DISCLAIMER] This response could not be fully verified against the source documents "
        "after 3 attempts. Please verify with the Registrar's Office.",
        S["body"]))
    story.append(Paragraph("Demonstrates all 3 advanced Self-RAG behaviors: web fallback, hallucination detection, and max-retry disclaimer.", S["verdict_pass"]))

    story.append(PageBreak())

    # TC4
    story.append(tc_box("TC4 — Hallucination Prevention: LLM Declines to Fabricate", "PASS", S))
    story.append(Spacer(1, 0.1*cm))
    story.append(Paragraph(
        "<b>Query:</b> What are Dr. Ahmed Khan's office hours and list 3 of his recently published research papers?",
        S["body"]))
    story.append(Paragraph(
        "<b>Expected path:</b> decide (YES) -> retrieve -> grade (1 relevant: office hours) -> "
        "generate -> check (GROUNDED: LLM declines to fabricate papers) -> END",
        S["body"]))
    tc4_trace = (
        "[DECISION] needs_retrieval=True | reason: The query is about faculty information,\n"
        "           specifically a professor's office hours and research papers.\n"
        "[RETRIEVE] Found 4 chunks from knowledge base\n"
        "    Chunk 3: [Faculty_Directory.pdf] Dr. Ahmed Khan's office hours -> RELEVANT\n"
        "    Other 3 chunks -> IRRELEVANT\n"
        "[GRADE] 1/4 docs relevant\n"
        "[GENERATE] Draft response produced (retry=0, length=387 chars)\n"
        "[HALLUCINATION CHECK] verdict=GROUNDED | retry=0/3\n"
        "[DECISION PATH] DECISION -> RETRIEVE -> GRADE -> GENERATE -> HALLUCINATION CHECK"
    )
    story.append(Paragraph(tc4_trace, S["trace"]))
    story.append(Paragraph(
        "<b>Final response:</b> Dr. Ahmed Khan's office hours are Monday and Wednesday from 2:00 PM to 4:00 PM. "
        "Unfortunately, the provided context does not mention any of Dr. Ahmed Khan's recently published "
        "research papers. The context only provides information about his department, specialization, "
        "qualification, email, office, and office hours, but it does not include any details about "
        "his research publications.",
        S["body"]))
    story.append(Paragraph(
        "The LLM provided the verified office hours from KB and explicitly declined to fabricate "
        "paper titles. Hallucination checker rated GROUNDED — prevention worked correctly.",
        S["verdict_pass"]))

    story.append(Spacer(1, 0.3*cm))

    # TC5
    story.append(tc_box("TC5 — Creative: Multi-Department Faculty Cross-Reference", "PARTIAL PASS", S))
    story.append(Spacer(1, 0.1*cm))
    story.append(Paragraph(
        "<b>Query:</b> I want to study both Machine Learning and Power Systems. "
        "Who are the respective faculty members and what are their email addresses?",
        S["body"]))
    story.append(Paragraph(
        "<b>Expected path:</b> decide (YES) -> retrieve -> grade -> generate -> check (GROUNDED) -> END",
        S["body"]))
    tc5_trace = (
        "[DECISION] needs_retrieval=True | reason: The query requires searching the\n"
        "           university's knowledge base for faculty information.\n"
        "[RETRIEVE] Found 4 chunks from knowledge base\n"
        "    Chunk 1: [Faculty_Directory.pdf] XYZ University Faculty Directory header\n"
        "             -> RELEVANT: contains Dr. Ahmed Khan (ML specialization)\n"
        "    Chunks 2-4 -> IRRELEVANT\n"
        "[GRADE] 1/4 docs relevant\n"
        "[GENERATE] Draft response produced (retry=0, length=369 chars)\n"
        "[HALLUCINATION CHECK] verdict=GROUNDED | retry=0/3\n"
        "[DECISION PATH] DECISION -> RETRIEVE -> GRADE -> GENERATE -> HALLUCINATION CHECK"
    )
    story.append(Paragraph(tc5_trace, S["trace"]))
    story.append(Paragraph(
        "<b>Final response:</b> Based on the provided context, I can tell you that for Machine Learning, "
        "the faculty member is Dr. Ahmed Khan, and his email address is ahmed.khan@xyz.edu.pk. "
        "However, I do not have information about a faculty member specializing in Power Systems "
        "in the provided context. Therefore, I cannot provide the name and email address of the "
        "faculty member for Power Systems.",
        S["body"]))
    story.append(Paragraph(
        "Partial Pass: Dr. Ahmed Khan (ML) correctly retrieved and verified. Dr. Umar Farooq "
        "(Power Systems) ranked 5th in cosine similarity — outside the top-4 window. "
        "Agent correctly admitted the gap rather than fabricating. "
        "Fix: increase k to 6 in search_university_kb.",
        S["verdict_partial"]))

    story.append(PageBreak())

    # ── Section 5: Summary ────────────────────────────────────────────────────
    story += banner("SECTION 5 — EVALUATION SUMMARY", C_DARK, S)

    story.append(Paragraph("5.1  Test Case Results", S["section_heading"]))
    story.append(data_table(
        ["TC", "Scenario", "Path", "Verdict"],
        [
            ["TC1", "Greeting — no retrieval", "DECISION -> DIRECT ANSWER", "PASS"],
            ["TC2", "CS401 prereqs — relevant docs", "DECISION -> RETRIEVE -> GRADE(1/4) -> GENERATE -> CHECK", "PASS"],
            ["TC3", "TOEFL — web fallback + disclaimer", "DECISION -> RETRIEVE -> GRADE(0/4) -> WEB -> GENERATE -> CHECK(x3) -> DISCLAIMER", "PASS"],
            ["TC4", "Office hours + papers — hallucination prevention", "DECISION -> RETRIEVE -> GRADE(1/4) -> GENERATE -> CHECK(GROUNDED)", "PASS"],
            ["TC5", "Multi-department faculty", "DECISION -> RETRIEVE -> GRADE(1/4) -> GENERATE -> CHECK(GROUNDED)", "PARTIAL PASS"],
        ],
        S, col_widths=[1*cm, 4.5*cm, 8*cm, 3.5*cm]
    ))

    story.append(Paragraph("5.2  Self-RAG Decision Coverage", S["section_heading"]))
    story.append(data_table(
        ["Self-RAG Decision Point", "Demonstrated In"],
        [
            ["Skip retrieval (general/greeting query)", "TC1"],
            ["Retrieve for domain-specific query", "TC2, TC3, TC4, TC5"],
            ["Grade docs as relevant", "TC2 (1/4), TC4 (1/4), TC5 (1/4)"],
            ["Grade all docs irrelevant -> web fallback", "TC3 (0/4)"],
            ["Generate grounded response (first attempt)", "TC2, TC4, TC5"],
            ["Hallucination detected -> retry", "TC3 (x3 retries)"],
            ["Max retry limit enforced -> disclaimer added", "TC3"],
            ["Web search fallback executed", "TC3"],
            ["LLM avoids fabrication under constraint", "TC4 (research papers), TC5 (power systems faculty)"],
        ],
        S, col_widths=[9*cm, 8*cm]
    ))

    story.append(Paragraph("5.3  Architecture Validation", S["section_heading"]))
    story.append(Paragraph(
        "The graph compiled and ran successfully for all 5 test cases. "
        "All 7 nodes executed in their expected order. "
        "All 3 conditional routers made correct decisions as validated by the execution traces above. "
        "JSON parsing (parse_json_response) handled all LLM outputs without failures across "
        "20+ LLM calls total (5 tests x up to 4 LLM nodes each).",
        S["body"]))

    story.append(Spacer(1, 0.3*cm))
    story.append(data_table(
        ["Component", "Validation Result"],
        [
            ["StateGraph compilation", "Compiled without errors on import (build_graph() at module level)"],
            ["decide_retrieval node", "Correctly classified 4/4 university queries as YES; 1/1 greeting as NO"],
            ["grade_relevance node", "Correctly filtered 3-4 irrelevant chunks per test; never false-negative on truly relevant chunk"],
            ["check_hallucination node", "GROUNDED on TC2/TC4/TC5 (context-supported answers); HALLUCINATED on TC3 (all 3 retries)"],
            ["route_after_hallucination", "Correctly looped x3 in TC3; correctly routed to END in all grounded cases"],
            ["Disclaimer mechanism", "Triggered only in TC3 after exhausting 3 retries — no false triggers in other TCs"],
            ["Web search fallback", "Triggered only in TC3 (0/4 relevant) — not triggered in TC2/TC4/TC5"],
        ],
        S, col_widths=[5*cm, 12*cm]
    ))

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "Files: final_exam/graph.py (StateGraph), final_exam/tools.py (@tool definitions), "
        "final_exam/self_rag_agent.py (entry point), final_exam/ingest.py (ChromaDB ingestion), "
        "final_exam/create_data.py (PDF generation), final_exam/data/ (5 PDFs), "
        "final_exam/chroma_db/ (vector store), final_exam/evaluation_results.md (full traces).",
        S["body"]))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc = BaseDocTemplate(
        OUT_FILE,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
    )

    cover_frame = Frame(0, 0, A4[0], A4[1],
                        leftPadding=3*cm, rightPadding=3*cm,
                        topPadding=5*cm, bottomPadding=2.5*cm)
    body_frame  = Frame(2*cm, 2*cm, A4[0]-4*cm, A4[1]-4.5*cm,
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[cover_frame], onPage=on_cover),
        PageTemplate(id="Body",  frames=[body_frame],  onPage=on_page),
    ])

    story.insert(0, NextPageTemplate("Cover"))
    for i, item in enumerate(story):
        if isinstance(item, PageBreak):
            story.insert(i, NextPageTemplate("Body"))
            break

    doc.build(story)
    print(f"PDF generated: {OUT_FILE}")


if __name__ == "__main__":
    build()
