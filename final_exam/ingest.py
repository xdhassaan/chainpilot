"""
ingest.py — Part B: PDF Ingestion into ChromaDB
AI407L Final Exam, Spring 2026

Reads all 5 PDFs from data/, splits them into structured chunks,
adds metadata, and indexes them into a ChromaDB collection.

Usage:
    python ingest.py

Run this once before self_rag_agent.py.
"""

import os
import shutil

from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION  = "university_catalog"
EMBED_MODEL = "all-MiniLM-L6-v2"

# Maps filename → (department, doc_type)
PDF_METADATA = {
    "CS_Department_Catalog.pdf":        ("Computer Science",        "course_catalog"),
    "EE_Department_Catalog.pdf":        ("Electrical Engineering",  "course_catalog"),
    "BBA_Department_Catalog.pdf":       ("Business Administration", "course_catalog"),
    "University_Academic_Policies.pdf": ("University",              "academic_policy"),
    "Faculty_Directory.pdf":            ("University",              "faculty_directory"),
}


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def load_documents() -> list[Document]:
    docs = []
    for filename, (department, doc_type) in PDF_METADATA.items():
        pdf_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(pdf_path):
            print(f"  WARNING: {filename} not found — skipping. Run create_data.py first.")
            continue

        text = extract_text_from_pdf(pdf_path)
        docs.append(Document(
            page_content=text,
            metadata={
                "source":     filename,
                "department": department,
                "doc_type":   doc_type,
            },
        ))
        print(f"  Loaded: {filename} ({len(text)} chars)")
    return docs


def split_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for doc in docs:
        split = splitter.split_documents([doc])
        # Propagate parent metadata to every chunk
        for chunk in split:
            chunk.metadata.update(doc.metadata)
        chunks.extend(split)
    return chunks


def build_vectorstore(chunks: list[Document]):
    embeddings = SentenceTransformerEmbeddings(model_name=EMBED_MODEL)

    # Wipe and rebuild to keep things clean
    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR)
        print("  Cleared existing chroma_db/")

    vs = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION,
        persist_directory=CHROMA_DIR,
    )
    return vs


def main():
    print("=" * 50)
    print("  Self-RAG KB Ingestion — ingest.py")
    print("=" * 50)

    print("\n[1] Loading PDFs...")
    docs = load_documents()
    if not docs:
        print("ERROR: No documents loaded. Run create_data.py first.")
        return

    print(f"\n[2] Splitting into chunks (size=600, overlap=100)...")
    chunks = split_documents(docs)
    print(f"  Total chunks: {len(chunks)}")

    print(f"\n[3] Building ChromaDB collection '{COLLECTION}'...")
    vs = build_vectorstore(chunks)
    print(f"  Indexed {len(chunks)} chunks into {CHROMA_DIR}")

    print("\n[4] Sanity check — top 2 results for 'CS401 prerequisites':")
    results = vs.similarity_search("CS401 prerequisites", k=2)
    for i, r in enumerate(results, 1):
        print(f"  {i}. [{r.metadata.get('source')}] {r.page_content[:120]}...")

    print("\nIngestion complete. Run self_rag_agent.py to start the agent.")


if __name__ == "__main__":
    main()
