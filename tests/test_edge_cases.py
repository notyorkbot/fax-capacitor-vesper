"""Edge Case Test Suite for Fax Classification Pipeline

Tests specific edge cases: black/empty pages, malformed PDFs, JSON parsing,
and API error scenarios (all mocked - no actual API calls).
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
    EXPECTED_CLASSIFICATIONS,
    MAX_PAGES,
)


@pytest.fixture
def test_pdfs_dir():
    return Path("/tmp/fax-capacitor-vesper/data/synthetic-faxes")


@pytest.fixture
def orphan_cover_page_pdf(test_pdfs_dir):
    return test_pdfs_dir / "09_orphan_cover_page.pdf"


@pytest.fixture
def chart_dump_pdf(test_pdfs_dir):
    return test_pdfs_dir / "10_chart_dump_40pages.pdf"


@pytest.fixture
def misdirected_pdf(test_pdfs_dir):
    return test_pdfs_dir / "12_wrong_provider_misdirected.pdf"


@pytest.fixture
def mock_client_orphan_detected():
    client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text=json.dumps({
        "document_type": "other",
        "confidence": 0.88,
        "priority": "none",
        "extracted_fields": {},
        "flags": ["incomplete_document", "orphan_cover_sheet"],
    }))]
    mock_response.usage = Mock(input_tokens=1200, output_tokens=150)
    client.messages.create.return_value = mock_response
    return client


@pytest.fixture
def mock_client_multi_bundle_detected():
    client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text=json.dumps({
        "document_type": "other",
        "confidence": 0.75,
        "priority": "none",
        "flags": ["multi_document_bundle", "excessive_page_count"],
    }))]
    mock_response.usage = Mock(input_tokens=3500, output_tokens=200)
    client.messages.create.return_value = mock_response
    return client


@pytest.fixture
def mock_client_misdirected_detected():
    client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text=json.dumps({
        "document_type": "other",
        "confidence": 0.95,
        "priority": "none",
        "flags": ["possibly_misdirected", "wrong_recipient"],
    }))]
    mock_response.usage = Mock(input_tokens=1400, output_tokens=180)
    client.messages.create.return_value = mock_response
    return client


# ═══════════════════════════════════════════════════════════════════════════
# ORPHAN COVER PAGE TESTS (Case 09)
# ═══════════════════════════════════════════════════════════════════════════

class TestOrphanCoverPage:
    def test_orphan_cover_page_pdf_exists(self, orphan_cover_page_pdf):
        assert orphan_cover_page_pdf.exists()
    
    def test_orphan_cover_page_expected_as_other(self):
        assert EXPECTED_CLASSIFICATIONS["09_orphan_cover_page.pdf"] == "other"
    
    def test_orphan_cover_page_conversion(self, orphan_cover_page_pdf):
        images, total_pages, quality = pdf_to_base64_images(orphan_cover_page_pdf)
        assert total_pages == 1
        assert len(images) == 1
        decoded = base64.b64decode(images[0])
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n'
    
    def test_orphan_cover_page_classification(self, orphan_cover_page_pdf, mock_client_orphan_detected):
        images, total_pages, quality = pdf_to_base64_images(orphan_cover_page_pdf)
        result, usage = classify_document(images, total_pages, quality, mock_client_orphan_detected)
        assert result["document_type"] == "other"
        assert any(f in result["flags"] for f in ["incomplete_document", "orphan_cover_sheet"])


# ═══════════════════════════════════════════════════════════════════════════
# CHART DUMP TESTS (Case 10)
# ═══════════════════════════════════════════════════════════════════════════

class TestChartDumpMultiBundle:
    def test_chart_dump_pdf_exists(self, chart_dump_pdf):
        assert chart_dump_pdf.exists()
    
    def test_chart_dump_expected_as_other(self):
        assert EXPECTED_CLASSIFICATIONS["10_chart_dump_40pages.pdf"] == "other"
    
    def test_chart_dump_40_pages_total(self, chart_dump_pdf):
        import fitz
        doc = fitz.open(chart_dump_pdf)
        assert len(doc) == 40
        doc.close()
    
    def test_chart_dump_limited_processing(self, chart_dump_pdf):
        images, total_pages, quality = pdf_to_base64_images(chart_dump_pdf)
        assert total_pages == 40
        assert len(images) == MAX_PAGES
        assert len(images) < total_pages
    
    def test_chart_dump_multi_bundle_detection(self, chart_dump_pdf, mock_client_multi_bundle_detected):
        images, total_pages, quality = pdf_to_base64_images(chart_dump_pdf)
        result, usage = classify_document(images, total_pages, quality, mock_client_multi_bundle_detected)
        assert result["document_type"] == "other"
        assert any(f in result["flags"] for f in ["multi_document_bundle", "excessive_page_count"])


# ═══════════════════════════════════════════════════════════════════════════
# MISDIRECTED FAX TESTS (Case 12)
# ═══════════════════════════════════════════════════════════════════════════

class TestMisdirectedFax:
    def test_misdirected_pdf_exists(self, misdirected_pdf):
        assert misdirected_pdf.exists()
    
    def test_misdirected_expected_as_other(self):
        assert EXPECTED_CLASSIFICATIONS["12_wrong_provider_misdirected.pdf"] == "other"
    
    def test_misdirected_conversion(self, misdirected_pdf):
        images, total_pages, quality = pdf_to_base64_images(misdirected_pdf)
        assert total_pages >= 1
        for img in images:
            decoded = base64.b64decode(img)
            assert decoded[:8] == b'\x89PNG\r\n\x1a\n'
    
    def test_misdirected_detection(self, misdirected_pdf, mock_client_misdirected_detected):
        images, total_pages, quality = pdf_to_base64_images(misdirected_pdf)
        result, usage = classify_document(images, total_pages, quality, mock_client_misdirected_detected)
        assert result["document_type"] == "other"
        assert any(f in result["flags"] for f in ["possibly_misdirected", "wrong_recipient"])


# ═══════════════════════════════════════════════════════════════════════════
# BLACK/EMPTY PAGE DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestBlackEmptyPageDetection:
    def test_normal_page_not_blank(self, test_pdfs_dir):
        sample_pdf = test_pdfs_dir / "01_lab_result_cbc.pdf"
        images, _, _ = pdf_to_base64_images(sample_pdf)
        for img_b64 in images:
            decoded = base64.b64decode(img_b64)
            assert len(decoded) > 1000, "Normal page should produce substantial image"
    
    def test_page_quality_ratings(self, test_pdfs_dir):
        sample_pdf = test_pdfs_dir / "01_lab_result_cbc.pdf"
        images, _, quality = pdf_to_base64_images(sample_pdf)
        assert quality in ["good", "fair", "poor"]


# ═══════════════════════════════════════════════════════════════════════════
# MALFORMED PDF HANDLING TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestMalformedPdfHandling:
    def test_nonexistent_pdf_raises_exception(self):
        with pytest.raises(Exception):
            pdf_to_base64_images(Path("/nonexistent/fake.pdf"))
    
    def test_invalid_path_handling(self):
        with pytest.raises(Exception):
            pdf_to_base64_images(Path(""))
    
    def test_directory_instead_of_file(self, test_pdfs_dir):
        with pytest.raises(Exception):
            pdf_to_base64_images(test_pdfs_dir)


# ═══════════════════════════════════════════════════════════════════════════
# JSON PARSING EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════

class TestJsonParsingEdgeCases:
    def test_empty_json_response(self):
        client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="{}")]
        mock_response.usage = Mock(input_tokens=1000, output_tokens=10)
        client.messages.create.return_value = mock_response
        
        result, _ = classify_document(["img1"], 1, "good", client)
        assert result["document_type"] == "other"
        assert result["confidence"] == 0.0
    
    def test_partial_json_response(self):
        client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps({"document_type": "lab_result"}))]
        mock_response.usage = Mock(input_tokens=1000, output_tokens=50)
        client.messages.create.return_value = mock_response
        
        result, _ = classify_document(["img1"], 1, "good", client)
        assert result["document_type"] == "lab_result"
        assert result["confidence"] == 0.0
        assert result["flags"] == []
    
    def test_json_with_extra_fields(self):
        client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps({
            "document_type": "lab_result",
            "confidence": 0.9,
            "extra_field": "unexpected"
        }))]
        mock_response.usage = Mock(input_tokens=1000, output_tokens=50)
        client.messages.create.return_value = mock_response
        
        result, _ = classify_document(["img1"], 1, "good", client)
        assert result["document_type"] == "lab_result"
        assert "extra_field" in result
    
    def test_json_with_unicode(self):
        client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps({
            "document_type": "lab_result",
            "extracted_fields": {"patient_name": "José García"},
        }, ensure_ascii=False))]
        mock_response.usage = Mock(input_tokens=1000, output_tokens=50)
        client.messages.create.return_value = mock_response
        
        result, _ = classify_document(["img1"], 1, "good", client)
        assert "José García" in result["extracted_fields"]["patient_name"]
    
    def test_json_with_null_values(self):
        client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps({
            "document_type": "lab_result",
            "extracted_fields": {"patient_name": None, "sending_provider": "Dr. Smith"},
        }))]
        mock_response.usage = Mock(input_tokens=1000, output_tokens=50)
        client.messages.create.return_value = mock_response
        
        result, _ = classify_document(["img1"], 1, "good", client)
        assert result["extracted_fields"]["patient_name"] is None
        assert result["extracted_fields"]["sending_provider"] == "Dr. Smith"


# ═══════════════════════════════════════════════════════════════════════════
# API ERROR SCENARIOS (MOCKED)
# ═══════════════════════════════════════════════════════════════════════════

class TestApiErrorScenarios:
    def test_rate_limit_error(self):
        client = Mock()
        client.messages.create.side_effect = Exception("Rate limit exceeded")
        
        with pytest.raises(Exception) as exc_info:
            classify_document(["img1"], 1, "good", client)
        assert "rate limit" in str(exc_info.value).lower()
    
    def test_authentication_error(self):
        client = Mock()
        client.messages.create.side_effect = Exception("Invalid API key")
        
        with pytest.raises(Exception) as exc_info:
            classify_document(["img1"], 1, "good", client)
        assert "api" in str(exc_info.value).lower() or "key" in str(exc_info.value).lower()
    
    def test_timeout_error(self):
        client = Mock()
        client.messages.create.side_effect = Exception("Request timed out")
        
        with pytest.raises(Exception) as exc_info:
            classify_document(["img1"], 1, "good", client)
        assert "time" in str(exc_info.value).lower()
    
    def test_server_error(self):
        client = Mock()
        client.messages.create.side_effect = Exception("Internal server error")
        
        with pytest.raises(Exception) as exc_info:
            classify_document(["img1"], 1, "good", client)
        assert "server" in str(exc_info.value).lower() or "internal" in str(exc_info.value).lower()
