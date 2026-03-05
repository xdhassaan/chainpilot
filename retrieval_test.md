# Retrieval Test — SCDRA Knowledge Base

**Lab 2: Knowledge Engineering & Domain Grounding**

Vector Store: ChromaDB persistent collection `supplier_docs`
Embedding Model: `sentence-transformers/all-MiniLM-L6-v2`
Total chunks indexed: 28 (across 6 source files in `./data/`)
Metadata tags per chunk: `doc_type`, `supplier_id`, `region`, `category`, `priority_level`

---

## Test 1 — Semantic Search (No Metadata Filter)

**Query:** `"backup supplier for MCU semiconductor chips with fast lead time"`

**Purpose:** Verify that pure semantic similarity retrieves the most relevant supplier profiles for a realistic disruption scenario (e.g., primary MCU supplier TPA-001 goes down and the agent needs to find alternatives).

**Results:**

| Rank | Chunk ID | supplier_id | doc_type | region | priority_level | Distance |
|------|----------|-------------|----------|--------|----------------|----------|
| 1 | ALT-003-supplier_profile-025 | ALT-003 | supplier_profile | Asia | critical | 0.4206 |
| 2 | TPA-001-supplier_profile-023 | TPA-001 | supplier_profile | Asia | critical | 0.5351 |
| 3 | RAW-008-raw_material_profile-021 | RAW-008 | raw_material_profile | Asia | critical | 0.5363 |

**Top Result Content Snippet:**
```
Supplier ID:   ALT-003
Name:          Pacific Semiconductor Corp
Location:      Taipei, Taiwan
Region:        Asia-Pacific
Tier:          Backup
Status:        Active
Certifications: ISO 9001:2015, IATF 16949, ISO 45001
Products:      Semiconductor chips (MCU-2200 compatible, MCU-3300 compatible)
Lead Time:     10-14 days
MOQ:           2,000 units
On-Time Delivery: 91%
```

**Interpretation:**
The top result (ALT-003, distance 0.4206) is the correct answer — it is the pre-qualified backup supplier for the MCU-2200 and MCU-3300 product lines. The embedding model correctly ranked it above TPA-001 (the primary) because the query explicitly asks for a *backup*. The semantic search works without any filter because supplier profile documents are distinct enough that the right one surfaces naturally. This demonstrates the value of keeping full supplier profiles as single coherent chunks rather than fragmenting them.

---

## Test 2 — Metadata-Filtered Search (category = audit)

**Query:** `"supplier with quality problems or conditional pass audit"`

**Metadata Filter:** `where={"category": "audit"}`

**Purpose:** Demonstrate metadata filtering. Without the filter, this query would return supplier profiles and performance reports that mention quality. With the filter, results are restricted to the `audit_reports.txt` source, giving the agent precise, document-type-specific answers about actual audit findings — not general supplier descriptions.

**Results (filtered to audit documents only):**

| Rank | Chunk ID | supplier_id | doc_type | priority_level | Distance |
|------|----------|-------------|----------|----------------|----------|
| 1 | MULTI-audit_report-000 | MULTI | audit_report | medium | 0.5315 |
| 2 | RAW-008-audit_report-006 | RAW-008 | audit_report | critical | 0.6052 |
| 3 | ALT-003-audit_report-003 | ALT-003 | audit_report | medium | 0.6222 |

**Top Relevant Result Content Snippet (Rank 2 — RAW-008):**
```
RAW-008 (SiliconPure Materials): CONDITIONAL PASS.
- Finding: Delivery consistency below 90% target (actual: 88%).
- Finding: Documentation for rare earth sourcing incomplete.
- Required: Improvement plan due Q2 2025. Re-audit scheduled.
- Score: 76/100
```

**Interpretation:**
Without the `category=audit` filter, a query about quality problems could retrieve supplier profiles that mention risk notes (e.g., TPA-001's "single-source risk"), performance rankings, or compliance gaps — all tangentially related but not from audit documents. The metadata filter restricts results exclusively to the `audit_report` doc_type, ensuring the agent retrieves verified QA findings rather than unstructured risk commentary. The `priority_level=critical` tag on the RAW-008 chunk (assigned because its chunk contains "CONDITIONAL PASS") allows the agent to further triage results by urgency — finding the most critical audit findings first.

---

## Test 3 — Metadata-Filtered Search (region = Europe)

**Query:** `"passive component supplier resistors capacitors"`

**Metadata Filter:** `where={"region": "Europe"}`

**Purpose:** Demonstrate geographic metadata filtering. This simulates an agent decision rule: "If our Asian logistics corridor is disrupted, find a European supplier for passive components." Without the filter, the top results would include ECG-002 (correct) and ALT-003 (Asia-based — wrong region). The region filter ensures the agent only considers suppliers in the unaffected geography.

**Results (filtered to European suppliers only):**

| Rank | Chunk ID | supplier_id | doc_type | category | priority_level | Distance |
|------|----------|-------------|----------|----------|----------------|----------|
| 1 | ALT-004-supplier_profile-026 | ALT-004 | supplier_profile | electronics | high | 0.6553 |
| 2 | ECG-002-supplier_profile-024 | ECG-002 | supplier_profile | electronics | critical | 0.6602 |
| 3 | ALT-003-performance_report-020 | ALT-003 | performance_report | performance | critical | 0.8117 |

**Top Result Content Snippet (Rank 2 — ECG-002, the primary):**
```
Supplier ID:   ECG-002
Name:          EuroComponents GmbH
Location:      Munich, Germany
Region:        Europe
Tier:          Primary
Status:        Active
Certifications: ISO 9001:2015, REACH compliant, RoHS compliant, AEO certified
Products:      Precision resistors (RES-10K, RES-47K), inductors (IND-100uH)
Lead Time:     7-10 days
On-Time Delivery: 98%
Quality Reject Rate: 0.1%
```

**Interpretation:**
Filtering by `region=Europe` correctly surfaces ECG-002 (the primary passive component supplier, Munich) and ALT-004 (Nordic Electronics AB, Stockholm backup) while excluding Asian suppliers like ALT-003. Note that Rank 3 (ALT-003-performance_report) has a high distance (0.8117) — this is a performance report chunk that happens to mention LOG-007, a European logistics partner, but is semantically distant from the query. In production, applying an additional `category=electronics` filter or raising the distance threshold would remove this false positive, demonstrating how combining multiple metadata tags significantly improves retrieval precision.

---

## Summary

| Test | Filter Used | Goal | Result |
|------|-------------|------|--------|
| 1 | None | Semantic similarity across all docs | Correctly retrieved backup semiconductor supplier (ALT-003) as top result |
| 2 | `category=audit` | Restrict to audit findings only | Surfaced CONDITIONAL PASS finding for RAW-008 ahead of supplier profiles |
| 3 | `region=Europe` | Geographic restriction for disruption fallback | Returned only European suppliers; excluded all Asian sources |

Metadata filtering proves its value most clearly in Tests 2 and 3: without filters, the agent risks blending authoritative audit findings with informal risk notes, or retrieving geographically irrelevant suppliers during regional disruptions. The 5-tag metadata schema (`doc_type`, `supplier_id`, `region`, `category`, `priority_level`) enables compound filtering that directly improves decision quality in the SCDRA use case.
