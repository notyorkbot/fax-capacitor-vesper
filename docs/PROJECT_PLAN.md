# Fax Capacitor — Project Plan

> **Interview-ready prototype for AI-powered healthcare fax classification**

---

## 1. Problem Statement

### The Healthcare Fax Triage Problem

Despite decades of digitization, **75% of healthcare communication still occurs via fax**. For small healthcare practices (1–10 providers), this creates a daily operational burden:

| Metric | Reality |
|--------|---------|
| **Volume** | 30–80+ faxes per day |
| **Time** | 1–2 hours daily for manual sorting |
| **Risk** | Urgent items (critical lab values, prior auth denials) buried in the pile |
| **Staff** | One person (often practice manager) handling everything |
| **Cost** | $400–1,200/month in staff time at $20–30/hr |

### Current Workflow Pain Points

```
Cloud Fax Service → Email Inbox → Manual Download → Open PDF → 
Read & Understand → Decide Type → Assign Priority → Route to Provider/Queue

Time per document: 1–3 minutes
Daily burden: 30–80 documents × 1–3 min = 30–240 minutes
```

**Problems:**
1. **No prioritization**: Urgent and routine items look identical in the inbox
2. **No classification**: Staff must read every document to understand its type
3. **No automation**: Routing decisions are manual, repetitive, and error-prone
4. **No visibility**: No dashboard showing "what's urgent right now"

### Why Enterprise Solutions Don't Fit

| Solution | Cost | IT Requirements | Deployment Time | Fit for Small Practice? |
|----------|------|-----------------|-----------------|----------------------|
| Kofax | $50K+ | Dedicated IT | 3–6 months | ❌ No |
| OpenText | $30K+ | IT team | 2–4 months | ❌ No |
| Solarity | $25K+ | Integration specialist | 2–3 months | ❌ No |
| **Fax Capacitor** | **API costs only** | **Self-hosted** | **Hours** | ✅ **Yes** |

---

## 2. Solution Overview

### Core Value Proposition

> Transform an undifferentiated pile of fax PDFs into a **prioritized, classified queue** with extracted metadata — without requiring practices to change their existing workflows.

### How It Works

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   INGEST    │───▶│  CLASSIFY   │───▶│   EXTRACT   │───▶│   ROUTE     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     │                   │                   │                   │
     ▼                   ▼                   ▼                   ▼
 PDF upload      Claude Vision API    Patient name       Priority queue
 Email watch     Document type        Provider           Dashboard
 Folder drop     Confidence score     Date, urgency      EMR integration
```

### Key Differentiators

1. **No workflow disruption**: Works with existing cloud fax services (eFax, RingCentral)
2. **Intelligent classification**: Claude Vision understands context, not just OCR text
3. **Confidence calibration**: Low-confidence items flagged for human review
4. **Cost transparency**: ~$0.03–0.05 per document, predictable pricing
5. **Open architecture**: JSON output enables any downstream integration

---

## 3. Phase 1: MVP Scope (Current Build)

### What's Built

| Component | Status | Description |
|-----------|--------|-------------|
| **PDF Pipeline** | ✅ Complete | PyMuPDF rendering at 300 DPI |
| **Classification Core** | ✅ Complete | Claude Vision API integration |
| **Test Corpus** | ✅ Complete | 12 synthetic faxes (all types + edge cases) |
| **Cost Tracking** | ✅ Complete | Token usage and cost estimation |
| **Accuracy Validation** | ✅ Complete | Ground truth comparison, summary tables |

### Key Metrics

| Metric | Result |
|--------|--------|
| **Classification accuracy** | 75% (9/12 correct) |
| **Lines of code** | 355 (compact, readable) |
| **Processing time** | 2–4 seconds per document |
| **Cost per document** | ~$0.03–0.05 (300 DPI) |
| **Dependencies** | 3 core (anthropic, PyMuPDF, Pillow) |

### Edge Cases Handled

| Case | Strategy | Status |
|------|----------|--------|
| Multi-page documents | First 3 of 5+ pages | ✅ Implemented |
| Orphan cover pages | Classify as "other" + flag | ✅ Working |
| Misdirected faxes | Flag "possibly_misdirected" | ✅ Working |
| Marketing/junk | Auto-detect, low priority | ✅ Working |
| Poor scan quality | Quality assessment + processing | ⚠️ File-size heuristic (P0 fix) |

---

## 4. Phase 2: Vision (Next 2–4 Weeks)

### Dashboard & UI

| Feature | Description | Priority |
|---------|-------------|----------|
| **Priority queue** | Color-coded list by urgency | P1 |
| **Document viewer** | PDF preview + extracted metadata | P1 |
| **Action buttons** | Mark reviewed, reassign, flag, dismiss | P1 |
| **Filter/sort** | By type, priority, date, confidence | P2 |
| **Batch upload** | Drag-and-drop multiple files | P2 |

### Backend Enhancements

| Feature | Description | Priority |
|---------|-------------|----------|
| **API server** | FastAPI with REST endpoints | P1 |
| **Database** | SQLite → PostgreSQL migration path | P2 |
| **Email ingestion** | IMAP/POP3 auto-import | P2 |
| **Retry logic** | Exponential backoff for API failures | P0 |
| **Schema validation** | Pydantic models for safety | P0 |

### Agentic Capabilities

| Feature | Description | Timeline |
|---------|-------------|----------|
| **Pattern detection** | Identify missing data from specific senders | Phase 2b |
| **Automated follow-up** | Queue standardized request fax | Phase 2c |
| **Routing rules** | Auto-assign to nursing/billing/scheduling | Phase 2a |

---

## 5. Interview Talking Points

### 30-Second Elevator Pitch

> "Small healthcare practices receive 30–80 faxes daily — lab results, referrals, prior auths — all landing in an email inbox. One person spends 1–2 hours daily manually opening, reading, and routing each one. I built Fax Capacitor to transform that pile into a prioritized queue using Claude's Vision API. It classifies documents, extracts key metadata, and flags urgent items — all without disrupting their existing workflow."

### Problem Framing (Why This Matters)

- **Real pain point**: 75% of healthcare communication is still fax
- **Underserved market**: Small practices can't afford $50K+ enterprise solutions
- **Safety critical**: Missed urgent faxes can delay care
- **AI-native solution**: Rules-based systems fail on document variety; LLMs handle the long tail

### Technical Decisions (Show Your Work)

**Q: Why Claude vs. OCR + rules?**

> "Medical faxes are too varied for rules — every lab, hospital, and pharmacy uses different layouts and terminology. An LLM handles the long tail that regex patterns cannot. OCR gives you text; Claude gives you understanding."

**Q: Why 300 DPI?**

> "150 DPI misses fine print like lab reference ranges. 600 DPI is 4x the tokens for marginal accuracy gains. 300 DPI is the sweet spot — medical-grade quality at reasonable cost."

**Q: Why PyMuPDF?**

> "No external dependencies. pdf2image requires Poppler, which complicates deployment — especially in containers. PyMuPDF is pure Python, fast, and handles healthcare PDFs well."

**Q: How do you handle edge cases?**

> "Three categories of edge cases: orphan cover pages (classify as 'other'), misdirected faxes (flag for review), and multi-document bundles (classify by dominant content). The prompt includes explicit instructions for each."

### Architecture Discussion

**Q: Walk me through the pipeline.**

> "Three stages: Ingestion, Processing, Output. Ingestion converts PDF to images at 300 DPI using PyMuPDF. Processing sends those images to Claude Vision with a structured system prompt. Output is JSON with type, priority, extracted fields, and confidence. The whole pipeline is 355 lines of Python, single-pass, no queues or brokers."

**Q: How would you scale this?**

> "API-based architecture scales horizontally. For high-volume practices, add queue-based async processing. The bottleneck is API cost, not architecture — at $0.03/doc, 1,000 docs/day is $30/day, which most practices would pay given the labor savings."

**Q: What about HIPAA?**

> "This prototype uses synthetic data only. For production: BAA with Anthropic, encryption at rest and in transit, audit logging, and on-premise deployment. The lowest-risk path is keeping everything local — the only external call is to Claude's API."

### Business Model (If Asked)

**Q: What's the business model?**

> "SaaS subscription at $50–150/month per practice based on volume. API costs are roughly $0.03–0.05 per document. Value prop: saves 1–2 hours/day of staff time at $20–30/hr = $400–1,200/month in labor value."

**Q: Who's the buyer?**

> "Practice manager or office administrator — not the physician. This is an operations tool, not a clinical tool. The pitch is staff time savings and reduced risk of missed urgent documents."

### Meta-Narrative (The "So What")

**Q: Why did you build this?**

> "Two reasons. First, to demonstrate applied AI architecture for healthcare — a constrained, high-stakes domain where accuracy and reliability matter. Second, to show how Claude can be used throughout the development process: brainstorming the idea, designing the architecture, writing the code, and reviewing the implementation. This is exactly how enterprise customers should use the product."

### Honest Limitations (Show Maturity)

**What to acknowledge proactively:**

1. **75% accuracy is MVP-level**: "Production needs 90%+, which requires prompt iteration and possibly fine-tuning."

2. **No retry logic yet**: "API failures fail the document. Adding tenacity with exponential backoff is P0."

3. **Image quality detection is naive**: "Currently uses file size; needs pixel-level brightness/contrast analysis."

4. **No HIPAA compliance**: "Prototype only. Production requires BAA, encryption, audit logging."

5. **No real-world validation**: "Synthetic data proves the concept; real faxes would reveal new edge cases."

**How to frame limitations positively:**

> "I know exactly what needs improvement and have a prioritized roadmap. The P0 items — retry logic, image quality analysis, schema validation — would take this from prototype to production-ready. I've documented all of this in `IMPROVEMENT_PLAN.md`."

---

## 6. Demo Script (15–17 Minutes)

### Minute 0–2: Problem Statement

> "Small healthcare practices receive 30–80 faxes daily. Lab results, referrals, prior auths, pharmacy requests — all landing as PDFs in an email inbox. One staff member spends 1–2 hours daily manually opening, reading, classifying, and routing each one. Enterprise solutions exist but cost $50K+ and require IT staff — out of reach for small practices. I built Fax Capacitor to solve this."

### Minute 2–7: Live Walkthrough

1. **Show test corpus**: 12 synthetic faxes covering all types + edge cases
2. **Run classification**: `python scripts/test_classification.py`
3. **Walk through output**: Priority queue table with accuracy calculation
4. **Highlight edge cases**: Show misdirected fax flag, orphan cover page detection
5. **Show cost tracking**: Token usage and estimated cost breakdown

### Minute 7–12: Architecture Deep-Dive

1. **Three-stage pipeline**: Ingestion → Processing → Output
2. **Prompt engineering**: Show system prompt, explain design decisions
3. **Technology choices**: PyMuPDF, Claude Sonnet, 300 DPI rationale
4. **JSON output schema**: Show structured data format
5. **Known limitations**: Be honest about retry logic, image quality detection

### Minute 12–15: Phase 2 & Agentic Evolution

1. **Dashboard UI**: React priority queue, document viewer
2. **Email integration**: Hands-free ingestion from cloud fax services
3. **Agentic features**: Pattern detection → automated follow-up
4. **HIPAA path**: BAA, encryption, audit logging, on-premise deployment

### Minute 15–17: Meta-Narrative

> "I built this with Claude — not just the code, but the architecture, prompts, and review. Brainstorming → design → implementation → critical review. This is how enterprise customers should use Claude: as a collaborative partner for the entire development lifecycle."

---

## 7. Key Metrics to Memorize

| Metric | Value | Context |
|--------|-------|---------|
| **Healthcare fax volume** | 75% of communication | Industry statistic |
| **Daily fax load** | 30–80 documents | Small practice (1–10 providers) |
| **Manual processing time** | 1–2 hours/day | Staff burden |
| **Labor cost** | $400–1,200/month | At $20–30/hr |
| **Classification accuracy** | 75% (9/12) | Current MVP |
| **Lines of code** | 355 | Compact, readable |
| **Processing time** | 2–4 seconds/doc | End-to-end |
| **Cost per document** | $0.03–0.05 | Claude Sonnet at 300 DPI |
| **Monthly API cost** | ~$50–100 | At 50 docs/day |
| **Target subscription** | $50–150/month | Per practice |

---

## 8. Risk Acknowledgments (Show Judgment)

### Technical Risks

1. **Classification accuracy**: 75% is MVP-level; production needs 90%+
   - *Mitigation*: Prompt iteration, confidence thresholds, human-in-the-loop

2. **API reliability**: Single point of failure
   - *Mitigation*: Retry logic (P0), caching, fallback to manual queue

3. **Cost at scale**: High-volume practices could see significant API bills
   - *Mitigation*: Tiered pricing, 150 DPI option for high-volume, caching

### Business Risks

1. **HIPAA compliance**: Major barrier to production
   - *Mitigation*: On-premise deployment, BAA structure, audit logging

2. **EMR integration**: Practices may want direct integration
   - *Mitigation*: JSON API design, HL7/FHIR adapter (Phase 2)

3. **User adoption**: Staff may resist new workflow
   - *Mitigation*: Minimal disruption, dashboard feels like email inbox

---

## 9. Appendix: Document Type Reference

| Type | Priority | Extracted Fields | Example |
|------|----------|------------------|---------|
| **lab_result** | High | Patient, DOB, test type, values, reference ranges, critical flags | CBC showing elevated WBC |
| **prior_auth_decision** | High | Patient, procedure, decision (approved/denied), auth number, effective date, appeal deadline | Denial with 30-day appeal |
| **referral_response** | Medium-High | Patient, referring provider, specialist, visit date, findings, recommendations | Cardiology consult report |
| **pharmacy_request** | Medium | Patient, medication, request type (refill/prior auth), pharmacy | Walgreens refill request |
| **insurance_correspondence** | Low-Medium | Patient, claim number, EOB details, coverage changes | Medicare EOB statement |
| **records_request** | Medium | Requestor, patient, records needed, purpose, legal authority | Attorney requesting records |
| **marketing_junk** | None | Sender, product/service, call to action | Equipment sales pitch |
| **other** | Review | Best-effort extraction | Orphan cover page, illegible scan |

---

*Last updated: 2026-02-15 by Polish Agent*
*For Anthropic Solutions Architect interview preparation*
