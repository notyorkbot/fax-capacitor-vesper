# Fax Capacitor — Technical Architecture

> **System design for AI-powered fax classification in healthcare practices**

---

## Executive Summary

Fax Capacitor implements a three-stage pipeline architecture: **Ingestion → Processing → Output**. Each stage has clear input/output contracts, enabling independent testing and incremental enhancement. The design prioritizes simplicity, debuggability, and cost transparency over premature optimization.

**Key Design Decisions:**
- PyMuPDF for PDF rendering (no external dependencies like Poppler)
- Single-pass Claude Vision API calls (OCR + understanding + extraction in one request)
- File-system based queue (no message broker complexity for MVP)
- JSON output (maximizes downstream integration flexibility)

---

## System Overview

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FAX CAPACITOR PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   INPUT     │───▶│  INGESTION  │───▶│  PROCESSING │───▶│   OUTPUT    │  │
│  │             │    │             │    │             │    │             │  │
│  │ • PDF files │    │ PyMuPDF     │    │ Claude API  │    │ JSON file   │  │
│  │ • Email     │    │ • Render    │    │ • Classify  │    │ • Results   │  │
│  │ • Upload    │    │ • Paginate  │    │ • Extract   │    │ • Metadata  │  │
│  └─────────────┘    │ • Quality   │    │ • Score     │    │ • Token use │  │
│                     └─────────────┘    └─────────────┘    └─────────────┘  │
│                           │                   │                             │
│                           ▼                   ▼                             │
│                     ┌─────────────────────────────────┐                   │
│                     │      VALIDATION & TRACKING      │                   │
│                     │  • Accuracy checking              │                   │
│                     │  • Token/cost tracking           │                   │
│                     │  • Error logging                  │                   │
│                     └─────────────────────────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
PDF Document
     │
     ▼
┌─────────────────────────────────────────┐
│  STAGE 1: INGESTION                     │
│  ─────────────────                      │
│  • File validation (PDF, size check)   │
│  • Page count detection                  │
│  • Render to PNG at 300 DPI (PyMuPDF)   │
│  • Image quality assessment              │
└─────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│  STAGE 2: PROCESSING                    │
│  ───────────────────                    │
│  • Build multi-image prompt              │
│  • Claude Vision API call               │
│  • Structured JSON response extraction   │
│  • Field validation (setdefaults)        │
└─────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│  STAGE 3: OUTPUT                        │
│  ──────────────                         │
│  • Classification result object            │
│  • Accuracy comparison (if ground truth)│
│  • Token usage tracking                  │
│  • JSON serialization                    │
└─────────────────────────────────────────┘
     │
     ▼
Dashboard / EMR / Routing Rules
```

---

## Component Breakdown

### 1. PDF Ingestion Layer

**Responsibility:** Accept PDF inputs and convert to normalized images for Vision API consumption.

**Implementation:** `pdf_to_base64_images()` in `scripts/test_classification.py` (lines 96-118)

**Key Behaviors:**
| Feature | Implementation | Rationale |
|---------|---------------|-----------|
| DPI | 300 (configurable) | Balance of quality vs. token cost |
| Page limits | First 3 of 5+ pages | Diminishing returns beyond 3 pages |
| Multi-page | All pages if ≤5 pages | Capture full context for short docs |
| Format | PNG via PyMuPDF | No Poppler dependency |
| Quality detection | File-size based (P0 improvement: pixel analysis) | Fast but naive |

**Output Contract:**
```python
Tuple[
    List[str],      # base64-encoded PNG images (one per page)
    int,            # total_page_count (for reference)
    str             # overall_quality: 'good' | 'fair' | 'poor'
]
```

---

### 2. AI Classification Engine

**Responsibility:** Send images to Claude Vision API and extract structured classification data.

**Implementation:** `classify_document()` in `scripts/test_classification.py` (lines 121-181)

**API Configuration:**
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Model | `claude-sonnet-4-20250514` | Best cost/performance for vision tasks |
| Temperature | 0.0 | Deterministic classification |
| Max tokens | 1024 | Structured JSON fits comfortably |
| Timeout | Default (no custom retry) | P1: Add tenacity retry layer |

**Prompt Engineering Strategy:**

The system prompt (lines 44-93) implements several techniques for reliable output:

1. **Explicit role definition**: "You are a medical document classification system for Whispering Pines Family Medicine"
2. **Clear taxonomy**: 8 document types with definitions and examples
3. **Priority rubric**: 5-level priority system with decision criteria
4. **Urgency indicators**: Explicit keyword list for pattern matching
5. **Misdirection detection**: Instructions to flag faxes intended for other providers
6. **Output schema**: Exact JSON structure required
7. **Confidence threshold**: "If confidence is below 0.65, set document_type to 'other'"
8. **Safety instructions**: "Be conservative with critical/high priority"

**Output Schema:**
```json
{
  "document_type": "lab_result",
  "confidence": 0.94,
  "priority": "high",
  "extracted_fields": {
    "patient_name": "Jane Doe",
    "patient_dob": "1980-03-15",
    "sending_provider": "Quest Diagnostics",
    "sending_facility": null,
    "document_date": "2026-02-10",
    "fax_origin_number": "555-0123",
    "urgency_indicators": ["CRITICAL VALUE", "ABNORMAL"],
    "key_details": "CBC showing elevated WBC count"
  },
  "is_continuation": false,
  "page_count_processed": 2,
  "page_quality": "good",
  "flags": []
}
```

---

### 3. Validation & Tracking Layer

**Responsibility:** Ensure output quality, track costs, and log errors.

**Accuracy Validation:**
- Ground truth map: `EXPECTED_CLASSIFICATIONS` dictionary (lines 28-42)
- Simple string match: `actual == expected`
- Edge cases intentionally misclassified by design (orphan pages → "other")

**Token & Cost Tracking:**
```python
@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    
    @property
    def estimated_cost(self) -> float:
        return (self.input_tokens * $3/million + 
                self.output_tokens * $15/million)
```

**Error Handling:**
| Error Type | Current Behavior | P0/P1 Improvement |
|------------|------------------|-------------------|
| API failure | Exception bubbles up, marks as error | Add retry with exponential backoff |
| JSON parse failure | Returns "other" with parse_error flag | Add markdown fence stripping, validation |
| Missing fields | `setdefault()` fills defaults | Pydantic schema validation |
| Black/low-quality pages | File-size heuristic | Pixel-level brightness/contrast analysis |

---

## Decision Log

### Why PyMuPDF (fitz) vs. pdf2image?

| Criterion | PyMuPDF | pdf2image |
|-----------|---------|-----------|
| External dependencies | None | Requires Poppler |
| Installation | `pip install PyMuPDF` | `brew/apt install poppler` |
| Rendering quality | Excellent at 300 DPI | Excellent at 300 DPI |
| Speed | Fast | Comparable |
| Page manipulation | Native | Via PIL |
| **Decision** | ✅ **Selected** | Fallback only if needed |

**Rationale**: Removing the Poppler dependency simplifies deployment, especially in containerized environments. PyMuPDF is a pure-Python solution with no system package requirements.

### Why Claude Sonnet vs. other models?

| Criterion | Claude Sonnet | GPT-4V | Gemini Pro |
|-----------|---------------|--------|------------|
| Document understanding | Excellent | Good | Good |
| Structured JSON output | Native mode | Function calling | Function calling |
| Vision + text in one call | ✅ Yes | ✅ Yes | ✅ Yes |
| Cost for 300 DPI images | $0.03–0.05/doc | $0.05–0.08/doc | $0.02–0.04/doc |
| Healthcare context handling | Excellent (conservative) | Good | Limited data |
| **Decision** | ✅ **Selected** | Alternative if needed | Not evaluated |

**Rationale**: Claude's conservative, safety-focused behavior is well-suited to healthcare applications. The structured JSON output mode eliminates parsing complexity.

### Why 300 DPI vs. 150 or 600?

| DPI | Token Cost | Accuracy | Recommendation |
|-----|------------|----------|----------------|
| 150 | ~50% of 300 | Good for typed docs | Acceptable for clean scans |
| **300** | **Baseline** | **Excellent** | **✅ Selected — best cost/accuracy** |
| 600 | ~4x of 300 | Marginally better | Diminishing returns |

**Rationale**: 300 DPI is the sweet spot for OCR/vision tasks. Medical documents often have fine print (lab reference ranges, footnotes) that 150 DPI may miss.

### Why file-size quality detection (temporary)?

**Current implementation** (naive):
```python
if len(img_bytes) > 500_000:
    qualities.append("good")
elif len(img_bytes) > 100_000:
    qualities.append("fair")
else:
    qualities.append("poor")
```

**Why it was chosen**: Fast to implement, requires no additional libraries.

**Why it must be replaced**: File size correlates weakly with visual quality. A high-contrast diagnostic image with little text may be small but excellent quality. A noisy scanned page may be large but poor quality.

**P0 replacement**: PIL/Pillow pixel analysis:
```python
def analyze_image_quality(img_bytes: bytes) -> Tuple[str, float]:
    img = Image.open(io.BytesIO(img_bytes)).convert('L')
    stat = ImageStat.Stat(img)
    mean_brightness = stat.mean[0]
    std_dev = stat.stddev[0]  # Contrast proxy
    
    # Quality by contrast, not file size
    if std_dev > 50:
        return "good", mean_brightness
    elif std_dev > 25:
        return "fair", mean_brightness
    else:
        return "poor", mean_brightness
```

---

## API Schema Reference

### Input to Classification Pipeline

```python
{
    "images": ["base64_png_1", "base64_png_2", ...],  # One per page processed
    "total_pages": 12,                                  # Original page count
    "page_quality": "good" | "fair" | "poor",          # Assessed quality
    "client": Anthropic                                 # API client instance
}
```

### Output from Classification Pipeline

```python
{
    "document_type": str,       # One of 8 taxonomy categories
    "confidence": float,        # 0.0–1.0 (recommend threshold: 0.65)
    "priority": str,            # critical | high | medium | low | none
    "extracted_fields": {
        "patient_name": str | None,
        "patient_dob": str | None,        # YYYY-MM-DD
        "sending_provider": str | None,
        "sending_facility": str | None,
        "document_date": str | None,      # YYYY-MM-DD
        "fax_origin_number": str | None,
        "urgency_indicators": [str],
        "key_details": str                # Human-readable summary
    },
    "is_continuation": bool,    # True if this is a continuation page
    "page_count_processed": int,
    "page_quality": str,
    "flags": [str]              # possibly_misdirected, incomplete_document, etc.
}
```

---

## Performance Characteristics

### Processing Time (M1 Mac, synthetic faxes)

| Document Type | Pages | Render Time | API Time | Total |
|---------------|-------|-------------|----------|-------|
| Lab result (simple) | 1 | 0.3s | 2.1s | 2.4s |
| Referral response | 2 | 0.5s | 2.8s | 3.3s |
| Chart dump (40 pages) | 3* | 0.8s | 3.5s | 4.3s |

*Limited to first 3 pages

### Cost Analysis (Claude Sonnet pricing)

| Document | Pages | Input Tokens | Output Tokens | Cost |
|----------|-------|--------------|---------------|------|
| Single page, simple | 1 | ~2,500 | ~250 | $0.012 |
| Multi-page, detailed | 3 | ~7,000 | ~400 | $0.036 |
| Average across corpus | 1.8 | ~2,935 | ~255 | $0.035 |

**At 50 documents/day**: ~$1.75/day, ~$52.50/month

---

## Phase 2: Agentic Evolution

The architecture supports future "agentic" capabilities without redesign:

### Automated Missing Data Detection

**Pattern:**
1. System tracks extracted fields per sending provider over time
2. Detects when a provider consistently omits key information (e.g., insurance info on referrals)
3. Phase 2a: Alert office staff to the pattern
4. Phase 2b: Generate and queue standardized follow-up fax

**Transition:** Pipeline (fixed flow) → Agent (observes → decides → acts)

### Email Inbox Integration

**Pattern:**
1. IMAP/POP3 listener monitors cloud fax delivery
2. PDF attachments auto-ingested matching fax patterns
3. Configurable filtering rules (sender, subject, attachment type)

---

## Security & Compliance Notes

### Current Prototype (Non-Compliant)

- ❌ No encryption at rest
- ❌ No audit logging
- ❌ No access controls
- ❌ No BAA with Anthropic
- ✅ Synthetic data only (no PHI)

### Production Path

1. **BAA**: Execute Business Associate Agreement with Anthropic
2. **Encryption**: At-rest (file system) and in-transit (TLS 1.3)
3. **Access Control**: Role-based (practice manager, front desk, clinical)
4. **Audit Logging**: All document access and classification decisions
5. **Data Retention**: Configurable policies per practice
6. **Deployment**: On-premise or private cloud (lowest risk)

---

## File Structure

```
fax-capacitor/
├── README.md                          # Entry point documentation
├── docs/
│   ├── ARCHITECTURE.md               # This document
│   ├── PROJECT_PLAN.md               # Problem, solution, roadmap
│   ├── COMPARISON.md                 # Side-by-side with Claude build
│   ├── CLASSIFICATION_TAXONOMY.md    # Document type definitions
│   └── AGENT_LOG.md                  # Build timeline and decisions
├── scripts/
│   └── test_classification.py        # Main classification pipeline (355 lines)
├── data/
│   └── synthetic-faxes/              # 12 test documents (fictional data)
├── prompts/
│   └── CLASSIFICATION_PROMPT.md      # System prompt for Claude API
├── requirements.txt                  # Python dependencies
└── .env.example                      # Configuration template
```

---

*Last updated: 2026-02-15 by Polish Agent*
