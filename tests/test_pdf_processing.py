"""Unit Test Suite for PDF Processing Pipeline

Tests PDF to image conversion, image encoding, multi-page logic without API calls.
Uses mocks for Anthropic responses.
"""

import os
import sys
import json
import base64
import pytest
from pathlib import Path
from unittest.mock import Mock
from dataclasses import asdict

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Import functions from test_classification (will mock API calls)
from test_classification import (
    pdf_to_base64_images,
    classify_document,
    TokenUsage,
    ClassificationResult,
    EXPECTED_CLASSIFICATIONS,
    MAX_PAGES,
    DPI,
)


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def test_pdfs_dir():
    """Return path to synthetic test PDFs."""
    return Path("/tmp/fax-capacitor-vesper/data/synthetic-faxes")


@pytest.fixture
def sample_pdf(test_pdfs_dir):
    """Return path to a sample single-page PDF."""
    return test_pdfs_dir / "01_lab_result_cbc.pdf"


@pytest.fixture
def multi_page_pdf(test_pdfs_dir):
    """Return path to 40-page chart dump."""
    return test_pdfs_dir / "10_chart_dump_40pages.pdf"


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client with realistic responses."""
    client = Mock()
    
    # Mock successful classification response
    mock_response = Mock()
    mock_response.content = [Mock(text=json.dumps({
        "document_type": "lab_result",
        "confidence": 0.95,
        "priority": "high",
        "extracted_fields": {
            "patient_name": "Test Patient",
            "patient_dob": "1985-03-15",
            "sending_provider": "Dr. Test",
            "sending_facility": "Test Lab",
            "document_date": "2026-02-14",
            "fax_origin_number": "555-123-4567",
            "urgency_indicators": [],
            "key_details": "CBC results"
        },
        "is_continuation": False,
        "flags": []
    }))]
    mock_response.usage = Mock(input_tokens=1500, output_tokens=250)
    
    client.messages.create.return_value = mock_response
    return client


@pytest.fixture
def mock_client_with_errors():
    """Create mock client that simulates various error conditions."""
    client = Mock()
    
    # Simulate API error
    client.messages.create.side_effect = Exception("API rate limit exceeded")
    return client


@pytest.fixture
def mock_client_invalid_json():
    """Create mock client that returns invalid JSON."""
    client = Mock()
    
    mock_response = Mock()
    mock_response.content = [Mock(text="not valid json {{[")]
    mock_response.usage = Mock(input_tokens=1500, output_tokens=50)
    
    client.messages.create.return_value = mock_response
    return client


@pytest.fixture
def mock_client_markdown_wrapped():
    """Create mock client that returns markdown-wrapped JSON."""
    client = Mock()
    
    mock_response = Mock()
    mock_response.content = [Mock(text='''```json
{
  "document_type": "lab_result",
  "confidence": 0.92,
  "priority": "medium",
  "extracted_fields": {},
  "flags": []
}
```''')]
    mock_response.usage = Mock(input_tokens=1500, output_tokens=200)
    
    client.messages.create.return_value = mock_response
    return client


# ═══════════════════════════════════════════════════════════════════════════
# PDF TO IMAGE CONVERSION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestPdfToImageConversion:
    """Test PDF to base64 image conversion without API dependencies."""
    
    def test_single_page_pdf_conversion(self, sample_pdf):
        """Test converting a single-page PDF to base64 images."""
        images, total_pages, quality = pdf_to_base64_images(sample_pdf)
        
        assert len(images) == 1, "Single page PDF should produce 1 image"
        assert total_pages == 1, "Total pages should be 1"
        assert total_pages <= 5, "Test PDF should have 5 or fewer pages"
        
        # Verify base64 encoding
        assert isinstance(images[0], str), "Image should be base64 string"
        decoded = base64.b64decode(images[0])
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n', "Should be PNG format"
    
    def test_base64_image_validity(self, sample_pdf):
        """Test that generated base64 images are valid and decodable."""
        images, _, _ = pdf_to_base64_images(sample_pdf)
        
        for img_b64 in images:
            # Should be valid base64
            decoded = base64.b64decode(img_b64)
            
            # Should be valid PNG (starts with PNG signature)
            assert decoded[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG signature"
            
            # Should have reasonable size (not empty/black page)
            assert len(decoded) > 1000, "Image too small, might be blank"
    
    def test_multi_page_pdf_limited_processing(self, multi_page_pdf):
        """Test that multi-page PDFs only process MAX_PAGES pages."""
        images, total_pages, quality = pdf_to_base64_images(multi_page_pdf)
        
        assert total_pages == 40, "Chart dump should have 40 pages"
        assert len(images) == MAX_PAGES, f"Should only process first {MAX_PAGES} pages"
        assert len(images) < total_pages, "Should process fewer pages than total"
    
    def test_image_quality_assessment(self, sample_pdf):
        """Test that image quality is assessed."""
        images, _, quality = pdf_to_base64_images(sample_pdf)
        
        assert quality in ["good", "fair", "poor"], f"Unexpected quality rating: {quality}"
    
    def test_dpi_setting_affects_output(self, sample_pdf):
        """Test that DPI setting produces expected image dimensions."""
        images, _, _ = pdf_to_base64_images(sample_pdf)
        
        # At 300 DPI, a letter page (8.5x11 inches) should be roughly:
        # 2550 x 3300 pixels
        decoded = base64.b64decode(images[0])
        
        # PNG files at 300 DPI should be reasonably large
        assert len(decoded) > 5000, "300 DPI image should be substantial"
    
    def test_nonexistent_pdf_raises_error(self):
        """Test that non-existent PDF raises appropriate error."""
        with pytest.raises(Exception):
            pdf_to_base64_images(Path("/nonexistent/path.pdf"))


# ═══════════════════════════════════════════════════════════════════════════
# MOCKED ANTHROPIC API TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestMockedClassification:
    """Test classification logic with mocked Anthropic API."""
    
    def test_successful_classification(self, mock_anthropic_client):
        """Test successful document classification with mock response."""
        dummy_images = ["base64img1", "base64img2"]
        
        result, usage = classify_document(dummy_images, 2, "good", mock_anthropic_client)
        
        # Verify API was called
        mock_anthropic_client.messages.create.assert_called_once()
        
        # Verify result structure
        assert "document_type" in result
        assert "confidence" in result
        assert "priority" in result
        assert "extracted_fields" in result
        assert "flags" in result
        
        # Verify usage tracking
        assert usage.input_tokens == 1500
        assert usage.output_tokens == 250
        assert usage.total_tokens == 1750
    
    def test_markdown_wrapped_json_handling(self, mock_client_markdown_wrapped):
        """Test that markdown-wrapped JSON is correctly parsed."""
        dummy_images = ["base64img1"]
        
        result, usage = classify_document(dummy_images, 1, "good", mock_client_markdown_wrapped)
        
        assert result["document_type"] == "lab_result"
        assert result["confidence"] == 0.92
        assert "flags" in result
    
    def test_invalid_json_response_handling(self, mock_client_invalid_json):
        """Test graceful handling of invalid JSON responses."""
        dummy_images = ["base64img1"]
        
        result, usage = classify_document(dummy_images, 1, "good", mock_client_invalid_json)
        
        # Should return safe defaults
        assert result["document_type"] == "other"
        assert result["confidence"] == 0.0
        assert "json_parse_error" in result["flags"]
        assert "parse_error" in result
    
    def test_api_error_handling(self, mock_client_with_errors):
        """Test that API errors propagate correctly."""
        dummy_images = ["base64img1"]
        
        with pytest.raises(Exception) as exc_info:
            classify_document(dummy_images, 1, "good", mock_client_with_errors)
        
        assert "rate limit" in str(exc_info.value).lower()
    
    def test_default_values_in_response(self, mock_anthropic_client):
        """Test that missing fields get default values."""
        # Create response with minimal data
        minimal_response = Mock()
        minimal_response.content = [Mock(text=json.dumps({
            "document_type": "lab_result"
            # Missing confidence, priority, extracted_fields, flags
        }))]
        minimal_response.usage = Mock(input_tokens=1000, output_tokens=100)
        
        mock_anthropic_client.messages.create.return_value = minimal_response
        
        dummy_images = ["base64img1"]
        result, _ = classify_document(dummy_images, 1, "good", mock_anthropic_client)
        
        assert result["confidence"] == 0.0
        assert result["priority"] == "none"
        assert result["extracted_fields"] == {}
        assert result["flags"] == []


# ═══════════════════════════════════════════════════════════════════════════
# TOKEN USAGE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestTokenUsage:
    """Test token usage tracking and cost calculation."""
    
    def test_token_usage_calculation(self):
        """Test token usage tracking."""
        usage = TokenUsage(input_tokens=1000, output_tokens=200)
        
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 200
        assert usage.total_tokens == 1200
    
    def test_cost_estimation(self):
        """Test cost estimation based on token counts."""
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        
        # Input: $3.00 per million, Output: $15.00 per million
        expected_cost = 3.00 + 15.00
        assert abs(usage.estimated_cost - expected_cost) < 0.01
    
    def test_zero_tokens(self):
        """Test with zero tokens."""
        usage = TokenUsage()
        
        assert usage.total_tokens == 0
        assert usage.estimated_cost == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# EXPECTED CLASSIFICATIONS VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestExpectedClassifications:
    """Validate expected classifications map and test data integrity."""
    
    def test_all_expected_classifications_present(self, test_pdfs_dir):
        """Verify all 12 test PDFs have expected classifications."""
        pdf_files = sorted([f for f in test_pdfs_dir.iterdir() if f.suffix.lower() == ".pdf"])
        pdf_names = [f.name for f in pdf_files]
        
        for pdf_name in pdf_names:
            assert pdf_name in EXPECTED_CLASSIFICATIONS, f"Missing expected classification for {pdf_name}"
    
    def test_expected_document_types_valid(self):
        """Verify all expected document types are in valid set."""
        valid_types = {
            "lab_result",
            "referral_response",
            "prior_auth_decision",
            "pharmacy_request",
            "insurance_correspondence",
            "records_request",
            "marketing_junk",
            "other"
        }
        
        for pdf_name, doc_type in EXPECTED_CLASSIFICATIONS.items():
            assert doc_type in valid_types, f"Invalid document type '{doc_type}' for {pdf_name}"
    
    def test_edge_cases_marked_as_other(self):
        """Verify edge cases are correctly expected to be 'other'."""
        edge_cases = [
            "09_orphan_cover_page.pdf",
            "10_chart_dump_40pages.pdf",
            "12_wrong_provider_misdirected.pdf"
        ]
        
        for case in edge_cases:
            assert EXPECTED_CLASSIFICATIONS[case] == "other", f"{case} should be classified as 'other'"
    
    def test_expected_count_is_12(self):
        """Verify we have exactly 12 test cases."""
        assert len(EXPECTED_CLASSIFICATIONS) == 12


# ═══════════════════════════════════════════════════════════════════════════
# IMAGE ENCODING/DECODING TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestImageEncoding:
    """Test image encoding and decoding."""
    
    def test_base64_roundtrip(self, sample_pdf):
        """Test that images can be encoded and decoded."""
        images, _, _ = pdf_to_base64_images(sample_pdf)
        
        for img_b64 in images:
            decoded = base64.b64decode(img_b64)
            re_encoded = base64.b64encode(decoded).decode('utf-8')
            assert re_encoded == img_b64, "Base64 roundtrip failed"
    
    def test_png_header_validation(self, sample_pdf):
        """Test PNG header bytes."""
        images, _, _ = pdf_to_base64_images(sample_pdf)
        
        for img_b64 in images:
            decoded = base64.b64decode(img_b64)
            png_signature = b'\x89PNG\r\n\x1a\n'
            assert decoded[:8] == png_signature, "Invalid PNG signature"
            assert decoded[12:16] == b'IHDR', "Missing IHDR chunk"


# ═══════════════════════════════════════════════════════════════════════════
# MULTI-PAGE LOGIC TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestMultiPageLogic:
    """Test multi-page processing logic."""
    
    def test_small_pdf_processes_all_pages(self, sample_pdf):
        """Test that small PDFs (<=5 pages) process all pages."""
        images, total_pages, _ = pdf_to_base64_images(sample_pdf)
        
        assert total_pages <= 5
        assert len(images) == total_pages, "Small PDFs should process all pages"
    
    def test_large_pdf_limits_pages(self, multi_page_pdf):
        """Test that large PDFs (>5 pages) only process MAX_PAGES."""
        images, total_pages, _ = pdf_to_base64_images(multi_page_pdf)
        
        assert total_pages > 5
        assert len(images) == MAX_PAGES, f"Large PDFs should only process {MAX_PAGES} pages"
    
    def test_page_count_reported_correctly(self, multi_page_pdf):
        """Test that total page count is correctly reported."""
        _, total_pages, _ = pdf_to_base64_images(multi_page_pdf)
        
        assert total_pages == 40, "Chart dump should have 40 pages"


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestConstants:
    """Validate module constants."""
    
    def test_dpi_setting(self):
        """Test DPI setting is reasonable."""
        assert DPI == 300, "DPI should be 300 for good quality"
        assert DPI >= 200, "DPI should be at least 200 for readable text"
    
    def test_max_pages_setting(self):
        """Test MAX_PAGES setting."""
        assert MAX_PAGES == 3, "MAX_PAGES should be 3"
        assert MAX_PAGES > 0, "MAX_PAGES should be positive"