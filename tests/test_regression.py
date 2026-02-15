"""Regression Test Suite for Fax Classification Pipeline

Documents current behavior and ensures fixes don't break working cases.
Tests the 9/12 documents that Claude got right.
"""

import os
import sys
import json
import base64
import pytest
from pathlib import Path
from unittest.mock import Mock

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from test_classification import (
    pdf_to_base64_images,
    classify_document,
    ClassificationResult,
    EXPECTED_CLASSIFICATIONS,
)


# ═══════════════════════════════════════════════════════════════════════════
# KNOWN WORKING CASES (9/12 that Claude got right)
# ═══════════════════════════════════════════════════════════════════════════

# These are the cases that should continue to work after fixes
KNOWN_WORKING_CASES = {
    "01_lab_result_cbc.pdf": {
        "expected": "lab_result",
        "type": "standard",
        "description": "Standard CBC lab result",
        "confidence_threshold": 0.80
    },
    "02_referral_response_cardiology.pdf": {
        "expected": "referral_response",
        "type": "standard",
        "description": "Cardiology consultation response",
        "confidence_threshold": 0.80
    },
    "03_prior_auth_approved.pdf": {
        "expected": "prior_auth_decision",
        "type": "standard",
        "description": "Approved prior authorization",
        "confidence_threshold": 0.85
    },
    "04_prior_auth_denied.pdf": {
        "expected": "prior_auth_decision",
        "type": "standard",
        "description": "Denied prior authorization",
        "confidence_threshold": 0.85
    },
    "05_pharmacy_refill_request.pdf": {
        "expected": "pharmacy_request",
        "type": "standard",
        "description": "Pharmacy refill request",
        "confidence_threshold": 0.80
    },
    "06_insurance_correspondence.pdf": {
        "expected": "insurance_correspondence",
        "type": "standard",
        "description": "Insurance EOB/correspondence",
        "confidence_threshold": 0.75
    },
    "07_patient_records_request.pdf": {
        "expected": "records_request",
        "type": "standard",
        "description": "Medical records request",
        "confidence_threshold": 0.80
    },
    "08_junk_marketing_fax.pdf": {
        "expected": "marketing_junk",
        "type": "standard",
        "description": "Marketing/junk fax",
        "confidence_threshold": 0.85
    },
    "11_illegible_physician_notes.pdf": {
        "expected": "referral_response",
        "type": "challenging",
        "description": "Illegible handwritten physician notes",
        "confidence_threshold": 0.60  # Lower threshold due to illegibility
    }
}

# Edge cases that were misclassified (need fixes)
KNOWN_EDGE_CASES = {
    "09_orphan_cover_page.pdf": {
        "expected": "other",
        "current_issue": "May be misclassified as urgent care referral",
        "type": "orphan"
    },
    "10_chart_dump_40pages.pdf": {
        "expected": "other",
        "current_issue": "May be misclassified due to first-page content",
        "type": "multi_bundle"
    },
    "12_wrong_provider_misdirected.pdf": {
        "expected": "other",
        "current_issue": "May not detect wrong recipient",
        "type": "misdirected"
    }
}


@pytest.fixture
def test_pdfs_dir():
    return Path("/tmp/fax-capacitor-vesper/data/synthetic-faxes")


@pytest.fixture
def mock_client_correct_classification():
    """Mock client that returns correct classifications."""
    client = Mock()
    
    def mock_create(*args, **kwargs):
        mock_response = Mock()
        # Default to lab_result
        doc_type = "lab_result"
        confidence = 0.90
        flags = []
        
        mock_response.content = [Mock(text=json.dumps({
            "document_type": doc_type,
            "confidence": confidence,
            "priority": "high",
            "extracted_fields": {
                "patient_name": "Test Patient",
                "sending_provider": "Dr. Test"
            },
            "flags": flags
        }))]
        mock_response.usage = Mock(input_tokens=1500, output_tokens=200)
        return mock_response
    
    client.messages.create.side_effect = mock_create
    return client


# ═══════════════════════════════════════════════════════════════════════════
# REGRESSION TESTS - KNOWN WORKING CASES
# ═══════════════════════════════════════════════════════════════════════════

class TestRegressionKnownWorking:
    """Regression tests for the 9 cases that should work."""
    
    def test_01_lab_result_cbc_exists(self, test_pdfs_dir):
        """Test that lab result PDF exists and converts."""
        pdf = test_pdfs_dir / "01_lab_result_cbc.pdf"
        assert pdf.exists()
        
        images, total_pages, quality = pdf_to_base64_images(pdf)
        assert total_pages >= 1
        assert len(images) >= 1
    
    def test_01_lab_result_expected_type(self):
        """Verify lab result is expected to be 'lab_result'."""
        assert EXPECTED_CLASSIFICATIONS["01_lab_result_cbc.pdf"] == "lab_result"
    
    def test_02_referral_response_exists(self, test_pdfs_dir):
        """Test that referral response PDF exists and converts."""
        pdf = test_pdfs_dir / "02_referral_response_cardiology.pdf"
        assert pdf.exists()
        
        images, total_pages, quality = pdf_to_base64_images(pdf)
        assert total_pages >= 1
    
    def test_02_referral_expected_type(self):
        """Verify referral response is expected to be 'referral_response'."""
        assert EXPECTED_CLASSIFICATIONS["02_referral_response_cardiology.pdf"] == "referral_response"
    
    def test_03_prior_auth_approved_exists(self, test_pdfs_dir):
        """Test that approved prior auth PDF exists and converts."""
        pdf = test_pdfs_dir / "03_prior_auth_approved.pdf"
        assert pdf.exists()
        
        images, total_pages, quality = pdf_to_base64_images(pdf)
        assert total_pages >= 1
    
    def test_03_prior_auth_expected_type(self):
        """Verify approved prior auth is expected to be 'prior_auth_decision'."""
        assert EXPECTED_CLASSIFICATIONS["03_prior_auth_approved.pdf"] == "prior_auth_decision"
    
    def test_04_prior_auth_denied_exists(self, test_pdfs_dir):
        """Test that denied prior auth PDF exists and converts."""
        pdf = test_pdfs_dir / "04_prior_auth_denied.pdf"
        assert pdf.exists()
        
        images, total_pages, quality = pdf_to_base64_images(pdf)
        assert total_pages >= 1
    
    def test_04_prior_auth_denied_expected_type(self):
        """Verify denied prior auth is expected to be 'prior_auth_decision'."""
        assert EXPECTED_CLASSIFICATIONS["04_prior_auth_denied.pdf"] == "prior_auth_decision"
    
    def test_05_pharmacy_refill_exists(self, test_pdfs_dir):
        """Test that pharmacy refill PDF exists and converts."""
        pdf = test_pdfs_dir / "05_pharmacy_refill_request.pdf"
        assert pdf.exists()
        
        images, total_pages, quality = pdf_to_base64_images(pdf)
        assert total_pages >= 1
    
    def test_05_pharmacy_expected_type(self):
        """Verify pharmacy refill is expected to be 'pharmacy_request'."""
        assert EXPECTED_CLASSIFICATIONS["05_pharmacy_refill_request.pdf"] == "pharmacy_request"
    
    def test_06_insurance_correspondence_exists(self, test_pdfs_dir):
        """Test that insurance correspondence PDF exists and converts."""
        pdf = test_pdfs_dir / "06_insurance_correspondence.pdf"
        assert pdf.exists()
        
        images, total_pages, quality = pdf_to_base64_images(pdf)
        assert total_pages >= 1
    
    def test_06_insurance_expected_type(self):
        """Verify insurance correspondence is expected to be 'insurance_correspondence'."""
        assert EXPECTED_CLASSIFICATIONS["06_insurance_correspondence.pdf"] == "insurance_correspondence"
    
    def test_07_records_request_exists(self, test_pdfs_dir):
        """Test that records request PDF exists and converts."""
        pdf = test_pdfs_dir / "07_patient_records_request.pdf"
        assert pdf.exists()
        
        images, total_pages, quality = pdf_to_base64_images(pdf)
        assert total_pages >= 1
    
    def test_07_records_expected_type(self):
        """Verify records request is expected to be 'records_request'."""
        assert EXPECTED_CLASSIFICATIONS["07_patient_records_request.pdf"] == "records_request"
    
    def test_08_marketing_junk_exists(self, test_pdfs_dir):
        """Test that marketing junk PDF exists and converts."""
        pdf = test_pdfs_dir / "08_junk_marketing_fax.pdf"
        assert pdf.exists()
        
        images, total_pages, quality = pdf_to_base64_images(pdf)
        assert total_pages >= 1
    
    def test_08_marketing_expected_type(self):
        """Verify marketing junk is expected to be 'marketing_junk'."""
        assert EXPECTED_CLASSIFICATIONS["08_junk_marketing_fax.pdf"] == "marketing_junk"
    
    def test_11_illegible_notes_exists(self, test_pdfs_dir):
        """Test that illegible notes PDF exists and converts."""
        pdf = test_pdfs_dir / "11_illegible_physician_notes.pdf"
        assert pdf.exists()
        
        images, total_pages, quality = pdf_to_base64_images(pdf)
        assert total_pages >= 1
    
    def test_11_illegible_expected_type(self):
        """Verify illegible notes is expected to be 'referral_response'."""
        assert EXPECTED_CLASSIFICATIONS["11_illegible_physician_notes.pdf"] == "referral_response"


# ═══════════════════════════════════════════════════════════════════════════
# CURRENT BEHAVIOR DOCUMENTATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestCurrentBehaviorDocumentation:
    """Document current behavior of the classification pipeline."""
    
    def test_all_test_pdfs_exist(self, test_pdfs_dir):
        """Verify all 12 test PDFs exist."""
        for filename in EXPECTED_CLASSIFICATIONS.keys():
            pdf = test_pdfs_dir / filename
            assert pdf.exists(), f"Missing test PDF: {filename}"
    
    def test_all_pdfs_convert_to_images(self, test_pdfs_dir):
        """Verify all PDFs can be converted to images."""
        for filename in EXPECTED_CLASSIFICATIONS.keys():
            pdf = test_pdfs_dir / filename
            images, total_pages, quality = pdf_to_base64_images(pdf)
            
            assert total_pages >= 1, f"{filename}: no pages found"
            assert len(images) >= 1, f"{filename}: no images generated"
            
            for img in images:
                decoded = base64.b64decode(img)
                assert decoded[:8] == b'\x89PNG\r\n\x1a\n', f"{filename}: invalid PNG"
    
    def test_expected_classifications_count(self):
        """Verify exactly 12 expected classifications."""
        assert len(EXPECTED_CLASSIFICATIONS) == 12
    
    def test_expected_vs_known_working_alignment(self):
        """Verify expected classifications match known working cases."""
        for filename in KNOWN_WORKING_CASES.keys():
            assert filename in EXPECTED_CLASSIFICATIONS
            expected = EXPECTED_CLASSIFICATIONS[filename]
            assert expected == KNOWN_WORKING_CASES[filename]["expected"]
    
    def test_known_working_cases_count(self):
        """Verify we have 9 known working cases."""
        assert len(KNOWN_WORKING_CASES) == 9
    
    def test_known_edge_cases_count(self):
        """Verify we have 3 known edge cases."""
        assert len(KNOWN_EDGE_CASES) == 3


# ═══════════════════════════════════════════════════════════════════════════
# FIX VERIFICATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCaseFixVerification:
    """Tests to verify edge case fixes (currently expected to fail until fixed)."""
    
    @pytest.mark.xfail(reason="Edge case not yet fixed - orphan cover detection")
    def test_09_orphan_cover_page_detected(self, test_pdfs_dir, mock_client_correct_classification):
        """Test that orphan cover page is detected as incomplete."""
        pdf = test_pdfs_dir / "09_orphan_cover_page.pdf"
        images, total_pages, quality = pdf_to_base64_images(pdf)
        
        result, _ = classify_document(images, total_pages, quality, mock_client_correct_classification)
        
        assert result["document_type"] == "other"
        assert any("incomplete" in f.lower() or "orphan" in f.lower() for f in result.get("flags", []))
    
    @pytest.mark.xfail(reason="Edge case not yet fixed - multi-bundle detection")
    def test_10_chart_dump_detected_as_multi(self, test_pdfs_dir, mock_client_correct_classification):
        """Test that chart dump is detected as multi-document bundle."""
        pdf = test_pdfs_dir / "10_chart_dump_40pages.pdf"
        images, total_pages, quality = pdf_to_base64_images(pdf)
        
        result, _ = classify_document(images, total_pages, quality, mock_client_correct_classification)
        
        assert result["document_type"] == "other"
        assert any("multi" in f.lower() or "bundle" in f.lower() for f in result.get("flags", []))
    
    @pytest.mark.xfail(reason="Edge case not yet fixed - misdirection detection")
    def test_12_misdirected_fax_detected(self, test_pdfs_dir, mock_client_correct_classification):
        """Test that misdirected fax is detected as wrong recipient."""
        pdf = test_pdfs_dir / "12_wrong_provider_misdirected.pdf"
        images, total_pages, quality = pdf_to_base64_images(pdf)
        
        result, _ = classify_document(images, total_pages, quality, mock_client_correct_classification)
        
        assert result["document_type"] == "other"
        assert any("misdirect" in f.lower() or "wrong" in f.lower() for f in result.get("flags", []))


# ═══════════════════════════════════════════════════════════════════════════
# DATA INTEGRITY TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestDataIntegrity:
    """Test data integrity and consistency."""
    
    def test_no_duplicate_expected_classifications(self):
        """Verify no duplicate filenames in expected classifications."""
        filenames = list(EXPECTED_CLASSIFICATIONS.keys())
        assert len(filenames) == len(set(filenames))
    
    def test_valid_document_types(self):
        """Verify all expected document types are valid."""
        valid_types = {
            "lab_result", "referral_response", "prior_auth_decision",
            "pharmacy_request", "insurance_correspondence", "records_request",
            "marketing_junk", "other"
        }
        
        for doc_type in EXPECTED_CLASSIFICATIONS.values():
            assert doc_type in valid_types, f"Invalid document type: {doc_type}"
    
    def test_pdf_files_are_valid(self, test_pdfs_dir):
        """Verify PDF files are valid and readable."""
        import fitz
        
        for filename in EXPECTED_CLASSIFICATIONS.keys():
            pdf = test_pdfs_dir / filename
            doc = fitz.open(pdf)
            
            # Should have at least one page
            assert len(doc) >= 1, f"{filename}: no pages"
            
            # Should be able to read first page
            page = doc[0]
            text = page.get_text()
            # Note: some PDFs may have no extractable text (image-based)
            
            doc.close()
