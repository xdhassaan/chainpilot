"""
ingest_data.py - RAG Ingestion Pipeline for the Supply Chain Disruption Response Agent

Lab 2: Knowledge Engineering & Domain Grounding
  Task 1 — Project-Specific Ingestion & Cleaning
  Task 2 — Semantic Chunking & Embedding
  Task 3 — Vector Indexing (ChromaDB)

Pipeline stages:
  1. Load raw supplier data files from ./data/
  2. Clean domain-specific noise (headers, footers, system tags, whitespace)
  3. Semantic chunking — split by logical record boundaries (one chunk = one supplier
     or one report section), keeping full profiles intact
  4. Metadata enrichment — attach 5 searchable tags per chunk:
       doc_type, supplier_id, region, category, priority_level
  5. Vectorize with sentence-transformers (all-MiniLM-L6-v2)
  6. Index into ChromaDB persistent collection "supplier_docs"

Usage:
    python ingest_data.py
"""

import os
import re
import glob
from datetime import datetime

import chromadb
from chromadb.utils import embedding_functions


# ═══════════════════════════════════════════════════════════════════════
#  STAGE 1: Load Raw Files
# ═══════════════════════════════════════════════════════════════════════

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load_raw_files(data_dir: str) -> list[dict]:
    """Load all .txt files from the data directory.

    Returns a list of dicts with 'filename', 'filepath', and 'raw_content'.
    """
    raw_files = []
    for filepath in sorted(glob.glob(os.path.join(data_dir, "*.txt"))):
        with open(filepath, "r", encoding="utf-8") as f:
            raw_files.append({
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "raw_content": f.read(),
            })
    print(f"[Load] Found {len(raw_files)} raw data files in {data_dir}/")
    return raw_files


# ═══════════════════════════════════════════════════════════════════════
#  STAGE 2: Cleaning
# ═══════════════════════════════════════════════════════════════════════

# Patterns that represent system noise, not domain content
NOISE_PATTERNS = [
    r"^={3,}.*?={3,}$",                         # ===== HEADER/FOOTER BANNERS =====
    r"^Generated:\s+\S+.*$",                     # Generated: 2025-01-15T08:30:00Z ...
    r"^---\s*(BEGIN|END)\s+RECORDS\s*---$",       # --- BEGIN/END RECORDS ---
    r"^Footer:.*$",                               # Footer: Confidential — ...
    r"^<<RECORD>>$",                              # <<RECORD>> delimiters
    r"^<<END RECORD>>$",                          # <<END RECORD>> delimiters
    r"<[^>]+>",                                   # Any HTML-like tags
]

NOISE_REGEX = re.compile(
    "|".join(f"({p})" for p in NOISE_PATTERNS),
    re.MULTILINE,
)


def clean_text(raw_text: str) -> str:
    """Strip domain-specific noise from raw exported text.

    Removes:
    - System export headers/footers (===== banners, Generated: lines, Footer: lines)
    - Record delimiters (<<RECORD>>, --- BEGIN/END RECORDS ---)
    - HTML-like tags
    - Excessive blank lines and leading/trailing whitespace
    """
    # Remove noise patterns
    cleaned = NOISE_REGEX.sub("", raw_text)

    # Collapse multiple blank lines into a single separator
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Strip leading/trailing whitespace per line and overall
    lines = [line.strip() for line in cleaned.splitlines()]
    cleaned = "\n".join(lines).strip()

    return cleaned


# ═══════════════════════════════════════════════════════════════════════
#  STAGE 3: Semantic Chunking
# ═══════════════════════════════════════════════════════════════════════

def semantic_chunk(cleaned_text: str, source_filename: str) -> list[dict]:
    """Split cleaned text into semantically meaningful chunks.

    Strategy: Each chunk represents one complete supplier record or one
    complete report section. We split on double-newline boundaries that
    separate distinct entities, ensuring a full supplier profile or
    audit finding stays together as a single retrievable unit.

    This respects the domain structure — a procurement analyst needs
    the complete supplier profile (certifications + capacity + risk notes)
    in one retrieval, not fragments split mid-sentence.
    """
    chunks = []

    # Split on double newlines — each block is a logical record
    raw_blocks = re.split(r"\n\n+", cleaned_text)

    # Merge small orphan blocks (< 50 chars) with the previous block
    merged_blocks = []
    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue
        if len(block) < 50 and merged_blocks:
            merged_blocks[-1] += "\n" + block
        else:
            merged_blocks.append(block)

    # Filter out blocks that are too short to be meaningful
    for block in merged_blocks:
        if len(block) >= 80:
            chunks.append({
                "content": block,
                "source_file": source_filename,
            })

    return chunks


# ═══════════════════════════════════════════════════════════════════════
#  STAGE 4: Metadata Enrichment
# ═══════════════════════════════════════════════════════════════════════

# Map source filenames to document types
DOC_TYPE_MAP = {
    "supplier_profiles.txt": "supplier_profile",
    "logistics_partners.txt": "logistics_profile",
    "raw_materials.txt": "raw_material_profile",
    "audit_reports.txt": "audit_report",
    "compliance_matrix.txt": "compliance_report",
    "performance_rankings.txt": "performance_report",
}

# Map source filenames to categories
CATEGORY_MAP = {
    "supplier_profiles.txt": "electronics",
    "logistics_partners.txt": "logistics",
    "raw_materials.txt": "raw_materials",
    "audit_reports.txt": "audit",
    "compliance_matrix.txt": "compliance",
    "performance_rankings.txt": "performance",
}


def extract_supplier_id(text: str) -> str:
    """Extract supplier ID from chunk text (e.g., TPA-001, LOG-006)."""
    match = re.search(r"\b([A-Z]{2,4}-\d{3})\b", text)
    return match.group(1) if match else "MULTI"


def extract_region(text: str) -> str:
    """Extract geographic region from chunk text using word-boundary matching."""
    text_lower = text.lower()

    # Check for explicit region labels first (most reliable)
    if "region:" in text_lower:
        if "asia" in text_lower.split("region:")[1][:30]:
            return "Asia"
        if "europe" in text_lower.split("region:")[1][:30]:
            return "Europe"
        if "north america" in text_lower.split("region:")[1][:30]:
            return "North America"

    # Fallback to location keywords (word-boundary via regex to avoid
    # false positives like "Busan" matching "usa")
    if re.search(r"\bnorth america\b", text_lower) \
       or re.search(r"\busa\b", text_lower) \
       or re.search(r"\btexas\b", text_lower) \
       or re.search(r"\baustin\b", text_lower):
        return "North America"
    if any(kw in text_lower for kw in [
        "europe", "germany", "sweden", "netherlands",
        "munich", "stockholm", "rotterdam",
    ]):
        return "Europe"
    if any(kw in text_lower for kw in [
        "asia", "china", "taiwan", "singapore", "korea",
        "shenzhen", "taipei", "dongguan", "busan",
    ]):
        return "Asia"
    return "Global"


def determine_priority(text: str, doc_type: str) -> str:
    """Determine priority level based on content signals.

    Priority levels:
    - critical: primary suppliers, high-risk items, conditional audit results
    - high: backup suppliers, specialty items, compliance gaps
    - medium: reports, rankings, general logistics
    """
    text_lower = text.lower()

    # Critical signals
    if any(kw in text_lower for kw in [
        "single-source", "conditional pass", "needs improvement",
        "tier:          primary", "tier:          specialty",
        "geopolitical risk", "factory has single production",
    ]):
        return "critical"

    # High signals
    if any(kw in text_lower for kw in [
        "tier:          backup", "corrective action", "pending",
        "improvement plan", "risk notes", "expedite surcharge",
    ]):
        return "high"

    return "medium"


def enrich_metadata(chunk: dict) -> dict:
    """Attach 5 searchable metadata tags to a chunk.

    Tags:
    1. doc_type        — Type of source document (supplier_profile, audit_report, etc.)
    2. supplier_id     — Supplier identifier extracted from content (TPA-001, etc.)
    3. region          — Geographic region (Asia, Europe, North America, Global)
    4. category        — Business category (electronics, logistics, compliance, etc.)
    5. priority_level  — Urgency classification (critical, high, medium)
    """
    source = chunk["source_file"]
    content = chunk["content"]

    chunk["metadata"] = {
        "doc_type": DOC_TYPE_MAP.get(source, "unknown"),
        "supplier_id": extract_supplier_id(content),
        "region": extract_region(content),
        "category": CATEGORY_MAP.get(source, "general"),
        "priority_level": determine_priority(content, DOC_TYPE_MAP.get(source, "")),
    }
    return chunk


# ═══════════════════════════════════════════════════════════════════════
#  STAGE 5 & 6: Vectorization & Indexing
# ═══════════════════════════════════════════════════════════════════════

CHROMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
COLLECTION_NAME = "supplier_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def build_vector_store(chunks: list[dict]) -> None:
    """Vectorize chunks and load into ChromaDB.

    Uses sentence-transformers (all-MiniLM-L6-v2) for local embeddings —
    no external API key required. Creates a persistent ChromaDB collection
    at ./chroma_db/ with the enriched metadata for filtered retrieval.
    """
    print(f"[Vector] Initializing embedding model: {EMBEDDING_MODEL}")
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    print(f"[Vector] Connecting to ChromaDB at {CHROMA_PATH}")
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Delete existing collection for clean re-ingestion
    try:
        client.delete_collection(name=COLLECTION_NAME)
        print(f"[Vector] Deleted existing '{COLLECTION_NAME}' collection.")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"description": "SCDRA supplier knowledge base — Lab 2"},
    )

    # Prepare batch data
    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        # Build a unique ID from doc_type and supplier_id
        sid = chunk["metadata"]["supplier_id"]
        dtype = chunk["metadata"]["doc_type"]
        chunk_id = f"{sid}-{dtype}-{i:03d}"

        ids.append(chunk_id)
        documents.append(chunk["content"])
        metadatas.append(chunk["metadata"])

    # Insert into ChromaDB (embeddings computed automatically)
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print(f"[Vector] Indexed {len(ids)} chunks into '{COLLECTION_NAME}' collection.")

    return collection


# ═══════════════════════════════════════════════════════════════════════
#  Verification
# ═══════════════════════════════════════════════════════════════════════

def verify_ingestion(collection) -> None:
    """Run verification queries to confirm the knowledge base works."""
    print("\n" + "=" * 60)
    print("  Verification Queries")
    print("=" * 60)

    # Query 1: Semantic search
    q1 = "alternative semiconductor chip supplier with fast lead time"
    results = collection.query(query_texts=[q1], n_results=3)
    print(f"\nQuery 1: '{q1}'")
    for doc_id, meta in zip(results["ids"][0], results["metadatas"][0]):
        print(f"  [{doc_id}] supplier={meta['supplier_id']}, "
              f"region={meta['region']}, priority={meta['priority_level']}")

    # Query 2: Metadata-filtered search
    q2 = "supplier quality audit results"
    results = collection.query(
        query_texts=[q2],
        n_results=3,
        where={"category": "audit"},
    )
    print(f"\nQuery 2 (filtered: category=audit): '{q2}'")
    for doc_id, meta in zip(results["ids"][0], results["metadatas"][0]):
        print(f"  [{doc_id}] supplier={meta['supplier_id']}, "
              f"doc_type={meta['doc_type']}, priority={meta['priority_level']}")

    # Query 3: Region-filtered search
    q3 = "European supplier for passive components"
    results = collection.query(
        query_texts=[q3],
        n_results=3,
        where={"region": "Europe"},
    )
    print(f"\nQuery 3 (filtered: region=Europe): '{q3}'")
    for doc_id, meta in zip(results["ids"][0], results["metadatas"][0]):
        print(f"  [{doc_id}] supplier={meta['supplier_id']}, "
              f"category={meta['category']}, priority={meta['priority_level']}")


# ═══════════════════════════════════════════════════════════════════════
#  Main Pipeline
# ═══════════════════════════════════════════════════════════════════════

def main():
    """Execute the full ingestion pipeline."""
    print("=" * 60)
    print("  SCDRA Knowledge Base — Ingestion Pipeline")
    print("  Lab 2: Knowledge Engineering & Domain Grounding")
    print("=" * 60)
    start = datetime.now()

    # Stage 1: Load
    raw_files = load_raw_files(DATA_DIR)
    if not raw_files:
        print("[Error] No data files found. Place .txt files in ./data/")
        return

    # Stage 2 & 3: Clean + Chunk
    all_chunks = []
    for raw in raw_files:
        print(f"\n[Clean] Processing {raw['filename']} "
              f"({len(raw['raw_content'])} chars raw)")
        cleaned = clean_text(raw["raw_content"])
        print(f"  -> {len(cleaned)} chars after cleaning "
              f"(removed {len(raw['raw_content']) - len(cleaned)} chars of noise)")

        chunks = semantic_chunk(cleaned, raw["filename"])
        print(f"  -> {len(chunks)} semantic chunks extracted")
        all_chunks.extend(chunks)

    # Stage 4: Metadata Enrichment
    print(f"\n[Metadata] Enriching {len(all_chunks)} chunks with 5 tags each...")
    for chunk in all_chunks:
        enrich_metadata(chunk)

    # Print enrichment summary
    print("\n[Metadata] Enrichment summary:")
    for chunk in all_chunks:
        m = chunk["metadata"]
        preview = chunk["content"][:60].replace("\n", " ")
        print(f"  {m['supplier_id']:>8} | {m['doc_type']:<22} | "
              f"{m['region']:<15} | {m['priority_level']:<8} | {preview}...")

    # Stage 5 & 6: Vectorize + Index
    print()
    collection = build_vector_store(all_chunks)

    # Verify
    verify_ingestion(collection)

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n{'=' * 60}")
    print(f"  Pipeline complete in {elapsed:.1f}s")
    print(f"  {len(all_chunks)} chunks indexed into ChromaDB")
    print(f"  Collection: '{COLLECTION_NAME}' at {CHROMA_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
