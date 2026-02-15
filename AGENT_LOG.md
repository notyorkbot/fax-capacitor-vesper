# Agent Build Log - Fax Capacitor Vesper

## Build Strategy

**Goal:** Parallel implementation of FaxTriage AI classification pipeline.
**Approach:** Multi-agent coordination with independent implementation.
**Comparison Target:** Claude Code build (`notyorkbot/fax-capacitor`)

## Agent Assignments

### Agent 1: Core Pipeline Implementation
- **Scope:** PDF→Image conversion, Claude API integration, basic CLI
- **Key Differences from Claude Build:** 
  - Evaluate alternative PDF libraries (pdf2image primary?)
  - Simpler error handling strategy
  - Different multi-page optimization approach
- **Deliverable:** Working `test_classification.py`

### Agent 2: Edge Case & Validation Layer
- **Scope:** Handle the 3 misclassified cases from Claude run
- **Focus:** Orphan pages, multi-document bundles, misdirection detection
- **Deliverable:** Enhanced validation logic, edge case handling

### Agent 3: Output Formatting & Documentation
- **Scope:** Results formatting, cost tracking, agent logging
- **Deliverable:** `AGENT_LOG.md` updates, comparison analysis, final docs

## Comparison Tracking

| Aspect | Claude Build | Vesper Build | Notes |
|--------|-------------|--------------|-------|
| PDF Rendering | PyMuPDF + pdf2image fallback | TBD | Agent 1 decision |
| Multi-page Strategy | First 3 of 5+ pages | TBD | Evaluate alternatives |
| Error Handling | Try/catch with fallbacks | TBD | Simpler vs robust |
| Cost Tracking | Detailed token counting | TBD | Match or simplify? |
| Edge Case Logic | Flag-based | TBD | Agent 2 focus |

## Timeline

- **09:00** - Agent 1 deployed
- **10:30** - Agent 2 deployed (if Agent 1 complete)
- **12:00** - Joint review with York
