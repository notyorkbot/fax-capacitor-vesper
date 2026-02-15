# Fax Capacitor Test Suite

Comprehensive test infrastructure for the FaxTriage AI classification pipeline.

## Overview

This test suite validates the classification pipeline without requiring API calls by using mocks and fixtures. It covers:

- **Unit tests** for PDF processing
- **Edge case tests** for the 3 challenging documents
- **Regression tests** for the 9 known working cases
- **Validation framework** for accuracy metrics

## Test Files

| File | Purpose | Test Count |
|------|---------|------------|
| `test_pdf_processing.py` | Unit tests for PDF→image conversion, encoding, multi-page logic | ~25 tests |
| `test_edge_cases.py` | Edge case tests (orphan pages, chart dumps, misdirected) | ~20 tests |
| `test_regression.py` | Regression tests for 9 working cases + data integrity | ~30 tests |
| `validation_runner.py` | Framework for comparing results to expected outcomes | CLI tool |

## Running Tests

### All Tests
```bash
cd /tmp/fax-capacitor-vesper
pytest tests/ -v
```

### Specific Test Files
```bash
pytest tests/test_pdf_processing.py -v
pytest tests/test_edge_cases.py -v
pytest tests/test_regression.py -v
```

### With Coverage
```bash
pytest tests/ --cov=scripts --cov-report=html
```

## Test Data

The test suite uses 12 synthetic PDFs in `/data/synthetic-faxes/`:

| # | Filename | Expected Type | Notes |
|---|----------|---------------|-------|
| 1 | `01_lab_result_cbc.pdf` | lab_result | Standard case |
| 2 | `02_referral_response_cardiology.pdf` | referral_response | Standard case |
| 3 | `03_prior_auth_approved.pdf` | prior_auth_decision | Standard case |
| 4 | `04_prior_auth_denied.pdf` | prior_auth_decision | Standard case |
| 5 | `05_pharmacy_refill_request.pdf` | pharmacy_request | Standard case |
| 6 | `06_insurance_correspondence.pdf` | insurance_correspondence | Standard case |
| 7 | `07_patient_records_request.pdf` | records_request | Standard case |
| 8 | `08_junk_marketing_fax.pdf` | marketing_junk | Standard case |
| 9 | `09_orphan_cover_page.pdf` | **other** | ⚠️ Edge case - orphan cover |
| 10 | `10_chart_dump_40pages.pdf` | **other** | ⚠️ Edge case - multi-bundle |
| 11 | `11_illegible_physician_notes.pdf` | referral_response | Challenging but works |
| 12 | `12_wrong_provider_misdirected.pdf` | **other** | ⚠️ Edge case - misdirected |

## Edge Cases

The 3 edge cases that require special handling:

### 09 - Orphan Cover Page
- **Challenge:** Cover sheet without attached content
- **Expected:** Classify as `other`, flag as `incomplete_document`
- **Current Issue:** May be misclassified based on cover content

### 10 - Chart Dump (40 pages)
- **Challenge:** Multi-document bundle with many pages
- **Expected:** Classify as `other`, flag as `multi_document_bundle`
- **Current Issue:** Only first 3 pages processed, may miss bundle nature

### 12 - Misdirected Fax
- **Challenge:** Wrong recipient/practice
- **Expected:** Classify as `other`, flag as `possibly_misdirected`
- **Current Issue:** May not detect wrong recipient

## Validation Framework

Run the validation framework after classification:

```bash
# After running test_classification.py
python tests/validation_runner.py /tmp/fax-capacitor-vesper/phase1_validation_results.json --table
```

Output includes:
- Overall accuracy percentage
- Edge case vs. standard case accuracy
- Misclassification details
- Comparison table

## Test Structure

### Unit Tests (`test_pdf_processing.py`)
- PDF to base64 image conversion
- PNG validation
- Multi-page limiting (MAX_PAGES)
- Quality assessment
- Mocked Anthropic API responses
- Token usage tracking
- JSON parsing edge cases

### Edge Case Tests (`test_edge_cases.py`)
- Orphan cover page detection
- Multi-document bundle detection
- Misdirected fax detection
- Black/empty page handling
- Malformed PDF handling
- JSON parsing scenarios
- API error scenarios

### Regression Tests (`test_regression.py`)
- Known working case validation
- Data integrity checks
- Fix verification tests (marked xfail until fixed)
- Expected classification alignment

## Adding New Tests

1. **For new edge cases:** Add to `test_edge_cases.py`
2. **For regression coverage:** Add to `test_regression.py`
3. **For unit tests:** Add to `test_pdf_processing.py`

## Mock Strategy

All API calls are mocked using `unittest.mock.Mock`:

```python
client = Mock()
mock_response = Mock()
mock_response.content = [Mock(text=json.dumps({
    "document_type": "lab_result",
    "confidence": 0.95,
    ...
}))]
client.messages.create.return_value = mock_response
```

This allows testing without:
- API keys
- Network calls
- API costs
- Rate limit concerns

## Success Criteria

The test suite validates:
- ✅ All 12 PDFs can be processed
- ✅ PDF→image conversion works
- ✅ Base64 encoding is valid
- ✅ Multi-page logic correct (limits to MAX_PAGES)
- ✅ Edge cases flagged appropriately
- ✅ Mock responses handled correctly
- ✅ JSON parsing edge cases covered
- ✅ API errors handled gracefully

## CI/CD Integration

```yaml
# .github/workflows/tests.yml example
- name: Run Tests
  run: |
    pip install pytest pytest-cov
    pytest tests/ -v --cov=scripts --cov-report=xml
```

## Notes

- No API calls are made during test runs
- All tests use synthetic PDFs in `/data/synthetic-faxes/`
- Tests validate the 9/12 working cases don't regress
- 3 edge case tests are marked `xfail` until fixed
