# Fax Capacitor - Build Comparison & Learning Notes

> **Purpose:** Side-by-side analysis of two independent implementations of the FaxTriage AI classification pipeline.  
> **Contributors:** Claude Code (Primary Build) + Vesper/Kimi (Parallel Agent Build)  
> **Status:** 🔄 In Progress — Notes added as builds complete

---

## 🎯 Build Philosophy Comparison

| Dimension | Claude Build (Reference) | Vesper Agent Build | Notes |
|-----------|-------------------------|-------------------|-------|
| **Primary Goal** | Production robustness | Simplicity & clarity | |
| **Approach** | Comprehensive handling | Happy-path focus | |
| **Code Philosophy** | Defensive programming | Readable minimalism | |
| **Library Choices** | PyMuPDF + pdf2image fallback | PyMuPDF only | |
| **Error Handling** | Multi-layer fallbacks | Basic try/catch | |
| **Edge Cases** | Proactive detection | Defer to iteration | |

---

## 📊 Accuracy Results

### Claude Build Results (Run: 2026-02-14 21:42 CST)
```
Accuracy: 9/12 (75%)
Token Usage: 35,223 input / 3,058 output
Est. Cost: ~$0.42
```

| File | Expected | Claude Result | Match | Notes |
|------|----------|---------------|-------|-------|
| 01_lab_result_cbc.pdf | lab_result | lab_result | ✅ | |
| 02_referral_response_cardiology.pdf | referral_response | referral_response | ✅ | |
| 03_prior_auth_approved.pdf | prior_auth_decision | prior_auth_decision | ✅ | |
| 04_prior_auth_denied.pdf | prior_auth_decision | prior_auth_decision | ✅ | |
| 05_pharmacy_refill_request.pdf | pharmacy_request | pharmacy_request | ✅ | |
| 06_insurance_correspondence.pdf | insurance_correspondence | insurance_correspondence | ✅ | |
| 07_patient_records_request.pdf | records_request | records_request | ✅ | |
| 08_junk_marketing_fax.pdf | marketing_junk | marketing_junk | ✅ | |
| 09_orphan_cover_page.pdf | **other** | referral_response | ⚠️ | Classified based on content description |
| 10_chart_dump_40pages.pdf | **other** | records_request | ⚠️ | Multi-type bundle, saw records cover |
| 11_illegible_physician_notes.pdf | referral_response | referral_response | ✅ | |
| 12_wrong_provider_misdirected.pdf | **other** | prior_auth_decision | ⚠️ | Flagged misdirection ✓ but typed content |

### Vesper Build Results
```
Accuracy: _/_ (_%)
Token Usage: _,___ input / _,___ output  
Est. Cost: $_.__
Run Date: 
```

| File | Expected | Vesper Result | Match | Notes |
|------|----------|---------------|-------|-------|
| (To be populated after test run) | | | | |

---

## 🔍 Code Structure Comparison

### File Organization

| Component | Claude Build | Vesper Build |
|-----------|-------------|--------------|
| **Main Script** | `scripts/test_classification.py` (420 lines) | `scripts/test_classification.py` (355 lines) |
| **Lines of Code** | ~420 | ~355 |
| **Key Functions** | 8 major functions | 6 major functions |
| **Dependencies** | anthropic, PyMuPDF, Pillow, python-dotenv, pdf2image | anthropic, PyMuPDF, Pillow |

### Key Implementation Differences

| Feature | Claude Approach | Vesper Approach | Claude Notes | Vesper Notes |
|---------|----------------|-----------------|--------------|--------------|
| **Black Page Detection** | Pixel-level brightness analysis | Size-based detection (simpler) | | |
| **PDF Fallback** | pdf2image (poppler) if PyMuPDF fails | None — trust PyMuPDF | | |
| **API Key Handling** | .env file + environment | Environment only | | |
| **Windows Encoding** | Explicit UTF-8 reconfiguration | Standard | | |
| **Type Hints** | Extensive | Minimal | | |
| **Cost Tracking** | Detailed token-by-token | Basic estimate | | |
| **Validation** | Full JSON schema validation | Basic field presence | | |

---

## 🧠 What We Learned

### Claude Build Insights
*(For Claude to fill in after review)*

- Edge case handling approach:
- Prompt engineering choices:
- Why the 3 "misses" aren't really misses:

### Vesper Build Insights
*(For Vesper to fill in after review)*

- Where simplicity helped:
- Where complexity was needed:
- Surprises during implementation:

### Cross-Build Learnings
*(Both contribute)*

| Topic | Claude Perspective | Vesper Perspective |
|-------|-------------------|-------------------|
| **Multi-agent vs single-agent** | | Used 3-agent coordination |
| **Error handling tradeoffs** | | |
| **Prompt stability** | | |
| **Cost optimization** | | |

---

## 🚀 Recommendations for Phase 2

### Consensus Improvements
*(Both builds agree on these)*

1. 
2. 
3. 

### Open Questions
*(Need discussion)*

1. 
2. 

### Picking the Winner
*(For York's Anthropic Interview)*

**Recommended approach:** [To be decided after comparison]

---

## 📝 How to Update This Doc

**Claude:** Edit via your normal workflow (Claude Code or direct commit)  
**Vesper:** Edit via `edit` tool or commit to `notyorkbot/fax-capacitor-vesper`  
**York:** Merge insights, add commentary, make final call

**Convention:** Use emoji status indicators — ✅ confirmed, ⚠️ observation, ❌ disagreement, 💡 idea

---

*Last Updated: 2026-02-15 07:35 CST — Framework created, awaiting test results*
