# Fax Capacitor

AI-powered fax classification and routing for small healthcare practices.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Anthropic Claude](https://img.shields.io/badge/AI-Claude%20Vision-orange.svg)](https://www.anthropic.com)

---

## Overview

Small healthcare practices receive 30–80+ faxes daily — lab results, referral responses, prior auth decisions, pharmacy requests, and junk mail — all landing as PDFs in an email inbox. A staff member manually opens, reads, classifies, and routes each one. This takes 1–2+ hours daily and risks burying urgent documents in the pile.

**Fax Capacitor** transforms an undifferentiated pile of inbound fax PDFs into a prioritized, classified queue using Claude's Vision API — without requiring practices to change their existing workflows.

### What It Does

1. **Ingest** — Accept fax PDFs (manual batch upload, folder watch, or email integration)
2. **Classify** — Claude Vision API reads each document, classifies by type, extracts key metadata, assigns priority
3. **Route** — Structured JSON output enables dashboard presentation, automated routing rules, and EMR integration

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))
- macOS, Linux, or Windows with WSL

### Installation

```bash
# Clone the repository
git clone https://github.com/notyorkbot/fax-capacitor.git
cd fax-capacitor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Set your Anthropic API key as an environment variable:

```bash
export ANTHROPIC_API_KEY='sk-ant-api-...'
```

Or create a `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-api-...
FAX_DPI=300
FAX_MAX_PAGES=3
FAX_MODEL=claude-sonnet-4-20250514
```

### Run Classification

```bash
# Run on the included synthetic test corpus
python scripts/test_classification.py

# Or specify custom directory
python scripts/test_classification.py --input /path/to/your/faxes
```

### Expected Output

```
================================================================================
FaxTriage AI Classification Pipeline
================================================================================

📄 Found 12 PDF files to process
🔑 Using model: claude-sonnet-4-20250514
📊 DPI: 300, Max pages per doc: 3

[1/12] Processing 01_lab_result_cbc.pdf... ✓ lab_result (conf: 0.94, time: 2.34s)
[2/12] Processing 02_referral_response_cardiology.pdf... ✓ referral_response (conf: 0.91, time: 2.12s)
...

================================================================================
Filename                             Expected             Actual               Match  Conf   Priority   Time     Flags
--------------------------------------------------------------------------------
01_lab_result_cbc.pdf                lab_result           lab_result           ✓      0.94   high       2.34s    -
02_referral_response_cardiology.pdf  referral_response    referral_response    ✓      0.91   medium     2.12s    -
...
--------------------------------------------------------------------------------

Accuracy: 9/12 (75.0%)

📊 Token Usage:
   Input tokens:  35,223
   Output tokens: 3,058
   Total tokens:  38,281
   Est. cost:     $0.42

✅ Results saved to: phase1_validation_results.json
================================================================================
```

---

## Architecture

### Data Flow

```
┌─────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│  PDF Ingestion  │────▶│  Claude Vision API  │────▶│  Structured JSON │
│                 │     │                    │     │                  │
│ • File upload   │     │ • Classification   │     │ • Type label     │
│ • Email watch   │     │ • Field extraction │     │ • Priority level │
│ • Folder watch  │     │ • Confidence score │     │ • Metadata       │
└─────────────────┘     └────────────────────┘     └──────────────────┘
        │                        │                         │
        ▼                        ▼                         ▼
   PyMuPDF (300 DPI)       Anthropic Claude         Dashboard / EMR
   Multi-page logic         Structured JSON          Routing rules
```

### Document Classification Taxonomy

| Type | Priority | Description | Example |
|------|----------|-------------|---------|
| **lab_result** | 🔴 High | Blood work, pathology, imaging | CBC with critical value |
| **prior_auth_decision** | 🔴 High | Insurance approval/denial notices | Prior auth denial with appeal deadline |
| **referral_response** | 🟡 Medium-High | Specialist notes, consult reports | Cardiology consult response |
| **pharmacy_request** | 🟡 Medium | Refill requests, formulary changes | Walgreens refill request |
| **insurance_correspondence** | 🟢 Low-Medium | EOBs, coverage changes | Medicare EOB statement |
| **records_request** | 🟢 Medium | Records requests | Attorney requesting records |
| **marketing_junk** | ⚫ None | Vendor solicitations | Equipment sales pitch |
| **other** | 🔵 Review | Unclassifiable or edge cases | Orphan cover page, misdirected fax |

### System Components

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **PDF Processor** | PyMuPDF | Page extraction, image rendering at 300 DPI |
| **Vision API** | Anthropic Claude Sonnet | Document understanding, classification, extraction |
| **Classifier** | Python 3.11 | Orchestration, result validation, cost tracking |
| **Output** | JSON | Structured data for downstream consumption |

---

## Comparison with Alternative Approaches

### vs. Traditional OCR + Rules

| Dimension | OCR + Regex Rules | Fax Capacitor (Claude Vision) |
|-----------|-------------------|-------------------------------|
| **Handling variation** | Fragile — breaks on new layouts | Robust — understands context |
| **Setup time** | Weeks of regex tuning | Hours of prompt engineering |
| **Long-tail documents** | Requires rule for every variant | Generalizes to unseen formats |
| **Confidence scoring** | None | Calibrated per-document |
| **Extraction depth** | Fixed fields | Semantic understanding |

### vs. Enterprise Fax Platforms

| Dimension | Enterprise (Kofax, OpenText) | Fax Capacitor |
|-----------|------------------------------|---------------|
| **Cost** | $50K+ implementation | Open source + API costs |
| **IT requirements** | Dedicated IT staff | Self-hosted, minimal config |
| **EMR integration** | Complex HL7/FHIR required | JSON output — bring your own integration |
| **Deployment time** | 3-6 months | Hours |
| **Customization** | Vendor-dependent | Full prompt control |

---

## Project Status

### ✅ What's Working

- **Core pipeline**: PDF → Images → Claude API → JSON (355 lines of Python)
- **Classification accuracy**: 75% (9/12) on synthetic test corpus
- **Cost efficiency**: ~$0.03–0.05 per document at 300 DPI
- **Multi-page handling**: Processes up to 3 pages for long documents
- **Edge case detection**: Flags for misdirected faxes, incomplete documents
- **Token tracking**: Detailed cost estimation for budget planning

### 🔄 In Progress

- **Image quality analysis**: Pixel-level brightness/contrast detection (not file-size based)
- **API resilience**: Retry logic with exponential backoff
- **JSON schema validation**: Pydantic models for response safety
- **Structured logging**: Replacing print statements with configurable logging

### 📋 Phase 2 Roadmap

- **Email inbox integration**: IMAP/POP3 auto-ingestion
- **Dashboard UI**: React-based priority queue interface
- **Agentic follow-up**: Automated pattern detection for missing data
- **Routing rules**: Automatic assignment to nursing, billing, or scheduling queues
- **HIPAA compliance path**: BAA structure, audit logging, encryption

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Technical deep-dive, data models, API schema |
| [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) | Problem statement, solution overview, interview talking points |
| [`docs/COMPARISON.md`](docs/COMPARISON.md) | Side-by-side with Claude Code build |
| [`docs/AGENT_LOG.md`](docs/AGENT_LOG.md) | Build timeline, decisions, learning outcomes |
| [`docs/CLASSIFICATION_TAXONOMY.md`](docs/CLASSIFICATION_TAXONOMY.md) | Detailed document types and extraction fields |

---

## Important Notes

- **⚠️ Synthetic data only**: All test documents use fictional patient data. No real PHI is included.
- **⚠️ Prototype status**: This is a demo implementation. Production deployment requires HIPAA compliance measures.
- **💡 Built with Claude**: This project demonstrates applied AI architecture using Claude for brainstorming, design, code generation, and review.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built for the Anthropic Solutions Architect interview process. February 2026.*
