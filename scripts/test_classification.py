#!/usr/bin/env python3
"""FaxTriage AI Classification Pipeline - Production Implementation

Robust fax classification with image quality analysis, API resilience, and structured logging.
"""

import os
import sys
import json
import base64
import io
import time
import logging
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass, asdict

import fitz
from PIL import Image, ImageStat
from anthropic import Anthropic, RateLimitError, APIError
from pydantic import BaseModel, Field, field_validator, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configuration
TEST_PDFS_DIR = Path("/tmp/fax-capacitor-vesper/data/synthetic-faxes")
OUTPUT_DIR = Path("/tmp/fax-capacitor-vesper")
RESULTS_FILE = OUTPUT_DIR / "phase1_validation_results.json"

DPI = 300
MAX_PAGES = 3
MAX_TOKENS = 1024
TEMPERATURE = 0
MODEL = "claude-sonnet-4-20250514"

CLAUDE_SONNET_INPUT_PRICE = 3.00 / 1_000_000
CLAUDE_SONNET_OUTPUT_PRICE = 15.00 / 1_000_000

# Quality thresholds
BLACK_PAGE_BRIGHTNESS_THRESHOLD = 15.0
BLACK_PAGE_CONTRAST_THRESHOLD = 10.0
QUALITY_GOOD_CONTRAST = 50.0
QUALITY_FAIR_CONTRAST = 25.0

API_MAX_RETRIES = 3
API_RETRY_MIN_WAIT = 4
API_RETRY_MAX_WAIT = 10

EXPECTED_CLASSIFICATIONS = {
    "01_lab_result_cbc.pdf": "lab_result",
    "02_referral_response_cardiology.pdf": "referral_response",
    "03_prior_auth_approved.pdf": "prior_auth_decision",
    "04_prior_auth_denied.pdf": "prior_auth_decision",
    "05_pharmacy_refill_request.pdf": "pharmacy_request",
    "06_insurance_correspondence.pdf": "insurance_correspondence",
    "07_patient_records_request.pdf": "records_request",
    "08_junk_marketing_fax.pdf": "marketing_junk",
    "09_orphan_cover_page.pdf": "other",
    "10_chart_dump_40pages.pdf": "other",
    "11_illegible_physician_notes.pdf": "referral_response",
    "12_wrong_provider_misdirected.pdf": "other",
}

CLASSIFICATION_PROMPT = """You are a medical document classification system for Whispering Pines Family Medicine. Analyze fax documents and return structured classification data.

## Document Types
- lab_result: Blood work, pathology, imaging reports
- referral_response: Specialist consultation notes, appointment confirmations
- prior_auth_decision: Insurance approval/denial notices
- pharmacy_request: Refill requests, formulary changes
- insurance_correspondence: EOBs, coverage changes
- records_request: Medical records requests
- marketing_junk: Vendor solicitations, catalogs
- other: Anything not matching above

## Priority Levels
- critical: Critical lab values, STAT results
- high: Abnormal labs, prior auth denials
- medium: Referral responses, pharmacy requests
- low: Insurance correspondence
- none: Marketing/junk

## Output Format (JSON only)
{
  "document_type": "string",
  "confidence": number (0.0-1.0),
  "priority": "string",
  "extracted_fields": {
    "patient_name": "string or null",
    "patient_dob": "string or null",
    "sending_provider": "string or null",
    "sending_facility": "string or null",
    "document_date": "string or null",
    "fax_origin_number": "string or null",
    "urgency_indicators": [],
    "key_details": "string"
  },
  "is_continuation": false,
  "page_count_processed": number,
  "page_quality": "string",
  "flags": []
}

## Rules
- Set unknown fields to null, don't guess
- If confidence < 0.65, use document_type "other"
- Be conservative with critical/high priority
- Flag possibly_misdirected if not for Dr. Sato"""


# Setup logging
def setup_logging(level: int = logging.INFO, log_file: Optional[Path] = None) -> logging.Logger:
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True
    )
    return logging.getLogger(__name__)


logger = logging.getLogger(__name__)


# Pydantic Models for JSON Validation
class ExtractedFields(BaseModel):
    patient_name: Optional[str] = None
    patient_dob: Optional[str] = None
    sending_provider: Optional[str] = None
    sending_facility: Optional[str] = None
    document_date: Optional[str] = None
    fax_origin_number: Optional[str] = None
    urgency_indicators: List[str] = Field(default_factory=list)
    key_details: Optional[str] = None


class ClassificationOutput(BaseModel):
    document_type: str = Field(pattern="^(lab_result|referral_response|prior_auth_decision|pharmacy_request|insurance_correspondence|records_request|marketing_junk|other)$")
    confidence: float = Field(ge=0.0, le=1.0)
    priority: str = Field(pattern="^(critical|high|medium|low|none)$")
    extracted_fields: ExtractedFields = Field(default_factory=ExtractedFields)
    is_continuation: bool = False
    page_count_processed: int = Field(ge=0)
    page_quality: str = Field(pattern="^(good|fair|poor)$")
    flags: List[str] = Field(default_factory=list)
    
    @field_validator('document_type')
    @classmethod
    def enforce_confidence_threshold(cls, v: str, info) -> str:
        values = info.data
        confidence = values.get('confidence', 0.0)
        if confidence < 0.65 and v != "other":
            logger.warning(f"Low confidence ({confidence:.2f}), forcing document_type to 'other'")
            return "other"
        return v


@dataclass
class ClassificationResult:
    filename: str
    expected: str
    actual: str
    match: bool
    confidence: float
    priority: str
    processing_time: float
    flags: list
    extracted_fields: dict
    api_response: dict
    error: Optional[str] = None


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    @property
    def estimated_cost(self) -> float:
        return self.input_tokens * CLAUDE_SONNET_INPUT_PRICE + self.output_tokens * CLAUDE_SONNET_OUTPUT_PRICE


@dataclass
class PageAnalysis:
    quality: str
    is_black: bool
    brightness: float
    contrast: float
    resolution: Tuple[int, int]


def analyze_image_quality(img_bytes: bytes) -> PageAnalysis:
    """Analyze image quality using actual pixel metrics (P0 FIX)."""
    try:
        img = Image.open(io.BytesIO(img_bytes))
    except Exception as e:
        raise ValueError(f"Failed to open image for analysis: {e}")
    
    resolution = img.size
    
    if img.mode != 'L':
        img_gray = img.convert('L')
    else:
        img_gray = img
    
    stat = ImageStat.Stat(img_gray)
    mean_brightness = stat.mean[0]
    std_dev = stat.stddev[0]
    
    # Real black page detection using pixel analysis
    is_mostly_black = (
        mean_brightness < BLACK_PAGE_BRIGHTNESS_THRESHOLD and 
        std_dev < BLACK_PAGE_CONTRAST_THRESHOLD
    )
    
    if is_mostly_black:
        logger.warning(f"Black page detected: brightness={mean_brightness:.1f}, contrast={std_dev:.1f}")
    
    # Quality based on contrast, not file size
    if std_dev > QUALITY_GOOD_CONTRAST and 30 < mean_brightness < 220:
        quality = "good"
    elif std_dev > QUALITY_FAIR_CONTRAST:
        quality = "fair"
    else:
        quality = "poor"
    
    logger.debug(f"Quality: {quality}, brightness={mean_brightness:.1f}, contrast={std_dev:.1f}")
    
    return PageAnalysis(quality, is_mostly_black, mean_brightness, std_dev, resolution)


def check_dpi_quality(resolution: Tuple[int, int], dpi: int = DPI) -> Tuple[bool, str]:
    """Validate resolution is adequate for OCR at target DPI."""
    width, height = resolution
    min_w = int(8.5 * 300 * 0.8)
    min_h = int(11 * 300 * 0.8)
    
    if width < min_w or height < min_h:
        return False, f"Resolution {width}x{height} below {dpi} DPI minimum ({min_w}x{min_h})"
    return True, f"Resolution {width}x{height} OK"


def pdf_to_base64_images(pdf_path: Path) -> Tuple[List[str], int, str, List[PageAnalysis]]:
    """Convert PDF to base64 images with quality analysis."""
    logger.debug(f"Opening PDF: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise ValueError(f"Failed to open PDF (corrupted?): {e}")
    
    total_pages = len(doc)
    pages_to_process = min(total_pages, MAX_PAGES) if total_pages > 5 else total_pages
    
    logger.info(f"Processing {pages_to_process} of {total_pages} pages from {pdf_path.name}")
    
    images = []
    page_analyses = []
    qualities = []
    black_pages = []
    
    for page_num in range(pages_to_process):
        try:
            page = doc[page_num]
            zoom = DPI / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            
            # P0: Real image quality analysis
            analysis = analyze_image_quality(img_bytes)
            page_analyses.append(analysis)
            qualities.append(analysis.quality)
            
            if analysis.is_black:
                black_pages.append(page_num + 1)
            
            is_adequate, dpi_msg = check_dpi_quality(analysis.resolution)
            if not is_adequate:
                logger.warning(f"Page {page_num + 1} has low resolution: {dpi_msg}")
            
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            images.append(b64)
            
        except Exception as e:
            logger.error(f"Failed to process page {page_num + 1}: {e}")
            raise RuntimeError(f"Page {page_num + 1} conversion failed: {e}")
    
    doc.close()
    
    # Determine overall quality
    if any(q == "poor" for q in qualities) or black_pages:
        overall_quality = "poor"
    elif all(q == "good" for q in qualities):
        overall_quality = "good"
    else:
        overall_quality = "fair"
    
    if black_pages:
        logger.warning(f"Document contains black pages: {black_pages}")
    
    return images, total_pages, overall_quality, page_analyses


def _create_api_content(images: List[str]) -> List[dict]:
    """Create API content payload with images."""
    content = [{"type": "text", "text": CLASSIFICATION_PROMPT}]
    for img_b64 in images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_b64}
        })
    return content


def _parse_api_response(response_text: str) -> dict:
    """Parse and clean API response text."""
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def _create_safe_fallback(page_count: int, page_quality: str, error_msg: str) -> dict:
    """Create safe fallback result on validation/parsing failure."""
    return {
        "document_type": "other",
        "confidence": 0.0,
        "priority": "none",
        "extracted_fields": {},
        "is_continuation": False,
        "page_count_processed": page_count,
        "page_quality": page_quality,
        "flags": ["parsing_error"],
        "error": error_msg
    }


# P0 FIX: API Resilience with retry logic
@retry(
    stop=stop_after_attempt(API_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=API_RETRY_MIN_WAIT, max=API_RETRY_MAX_WAIT),
    retry=retry_if_exception_type((RateLimitError, APIError)),
    before_sleep=lambda retry_state: logger.warning(
        f"API call failed (attempt {retry_state.attempt_number}), retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def classify_document(images: List[str], total_pages: int, page_quality: str, client: Anthropic) -> Tuple[dict, TokenUsage]:
    """Classify document with retry logic for transient failures."""
    content = _create_api_content(images)
    
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": content}]
        )
    except RateLimitError as e:
        logger.error(f"Rate limit hit: {e}")
        raise
    except APIError as e:
        logger.error(f"API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected API error: {e}")
        raise
    
    usage = TokenUsage(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens
    )
    
    try:
        result = _parse_api_response(response.content[0].text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        raw = response.content[0].text[:500] if response.content else ""
        return _create_safe_fallback(len(images), page_quality, f"JSON parse error: {e}"), usage
    
    # Add computed fields
    result["page_count_processed"] = len(images)
    result["page_quality"] = page_quality
    
    # P0 FIX: JSON Schema validation with Pydantic
    try:
        validated = ClassificationOutput.model_validate(result)
        return validated.model_dump(), usage
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        # Return safe fallback with raw response info
        fallback = _create_safe_fallback(len(images), page_quality, f"Validation error: {e}")
        fallback["raw_response_preview"] = response.content[0].text[:200] if response.content else ""
        return fallback, usage


def print_summary_table(results: List[ClassificationResult]) -> None:
    """Print formatted summary table."""
    print("\n" + "=" * 120)
    print(f"{'Filename':<40} {'Expected':<20} {'Actual':<20} {'Match':<6} {'Conf':<6} {'Priority':<10} {'Time':<8} {'Flags'}")
    print("-" * 120)
    
    for r in results:
        match_str = "✓" if r.match else "✗"
        flags_str = ", ".join(r.flags[:2]) if r.flags else "-"
        print(f"{r.filename:<40} {r.expected:<20} {r.actual:<20} {match_str:<6} "
              f"{r.confidence:<6.2f} {r.priority:<10} {r.processing_time:<8.2f} {flags_str}")
    
    print("-" * 120)
    
    correct = sum(1 for r in results if r.match)
    total = len(results)
    accuracy = (correct / total * 100) if total > 0 else 0
    
    print(f"\nAccuracy: {correct}/{total} ({accuracy:.1f}%)")


def main():
    """Main classification pipeline with comprehensive error handling."""
    # Setup logging
    log_file = OUTPUT_DIR / "classification.log"
    setup_logging(level=logging.INFO, log_file=log_file)
    
    logger.info("=" * 60)
    logger.info("FaxTriage AI Classification Pipeline - Production Build")
    logger.info("=" * 60)
    
    # Validate environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        print("\n❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Initialize client
    try:
        client = Anthropic(api_key=api_key)
        logger.info("Anthropic client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Anthropic client: {e}")
        print(f"\n❌ Error: Failed to initialize API client: {e}")
        sys.exit(1)
    
    # Find PDF files
    try:
        pdf_files = sorted([f for f in TEST_PDFS_DIR.iterdir() if f.suffix.lower() == ".pdf"])
        if not pdf_files:
            logger.error(f"No PDF files found in {TEST_PDFS_DIR}")
            print(f"❌ No PDF files found in {TEST_PDFS_DIR}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to read test directory: {e}")
        print(f"❌ Error accessing test directory: {e}")
        sys.exit(1)
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    print(f"\n📄 Found {len(pdf_files)} PDF files to process")
    print(f"🔑 Using model: {MODEL}")
    print(f"📊 DPI: {DPI}, Max pages per doc: {MAX_PAGES}")
    print(f"📝 Log file: {log_file}")
    print()
    
    results = []
    total_usage = TokenUsage()
    
    for i, pdf_path in enumerate(pdf_files, 1):
        filename = pdf_path.name
        expected = EXPECTED_CLASSIFICATIONS.get(filename, "unknown")
        
        print(f"[{i}/{len(pdf_files)}] Processing {filename}...", end=" ", flush=True)
        start_time = time.time()
        
        try:
            # Convert PDF to images with quality analysis
            images, total_pages, page_quality, page_analyses = pdf_to_base64_images(pdf_path)
            
            # Check for quality issues before API call
            black_pages = [i+1 for i, a in enumerate(page_analyses) if a.is_black]
            poor_quality_pages = [i+1 for i, a in enumerate(page_analyses) if a.quality == "poor"]
            
            if black_pages:
                logger.warning(f"{filename}: Black pages detected: {black_pages}")
            if poor_quality_pages:
                logger.warning(f"{filename}: Poor quality pages: {poor_quality_pages}")
            
            # Classify with retry logic (P0 fix)
            api_result, usage = classify_document(images, total_pages, page_quality, client)
            
            processing_time = time.time() - start_time
            actual = api_result.get("document_type", "other")
            match = (actual == expected)
            
            result = ClassificationResult(
                filename=filename,
                expected=expected,
                actual=actual,
                match=match,
                confidence=api_result.get("confidence", 0.0),
                priority=api_result.get("priority", "none"),
                processing_time=processing_time,
                flags=api_result.get("flags", []),
                extracted_fields=api_result.get("extracted_fields", {}),
                api_response=api_result
            )
            
            total_usage.input_tokens += usage.input_tokens
            total_usage.output_tokens += usage.output_tokens
            
            status = "✓" if match else "⚠"
            print(f"{status} {actual} (conf: {result.confidence:.2f}, time: {processing_time:.2f}s)")
            logger.info(f"Processed {filename}: {actual} (match={match}, conf={result.confidence:.2f})")
            
        except ValueError as e:
            # PDF corruption or malformed data
            processing_time = time.time() - start_time
            result = ClassificationResult(
                filename=filename,
                expected=expected,
                actual="error",
                match=False,
                confidence=0.0,
                priority="none",
                processing_time=processing_time,
                flags=["pdf_error"],
                extracted_fields={},
                api_response={},
                error=str(e)
            )
            print(f"✗ PDF ERROR: {e}")
            logger.error(f"PDF error for {filename}: {e}")
            
        except RuntimeError as e:
            # Page conversion failure
            processing_time = time.time() - start_time
            result = ClassificationResult(
                filename=filename,
                expected=expected,
                actual="error",
                match=False,
                confidence=0.0,
                priority="none",
                processing_time=processing_time,
                flags=["conversion_error"],
                extracted_fields={},
                api_response={},
                error=str(e)
            )
            print(f"✗ CONVERSION ERROR: {e}")
            logger.error(f"Conversion error for {filename}: {e}")
            
        except Exception as e:
            # Catch-all for unexpected errors
            processing_time = time.time() - start_time
            result = ClassificationResult(
                filename=filename,
                expected=expected,
                actual="error",
                match=False,
                confidence=0.0,
                priority="none",
                processing_time=processing_time,
                flags=["processing_error"],
                extracted_fields={},
                api_response={},
                error=str(e)
            )
            print(f"✗ ERROR: {e}")
            logger.exception(f"Unexpected error processing {filename}: {e}")
        
        results.append(result)
    
    print_summary_table(results)
    
    logger.info(f"Token Usage: input={total_usage.input_tokens}, output={total_usage.output_tokens}, cost=${total_usage.estimated_cost:.4f}")
    print(f"\n📊 Token Usage:")
    print(f"   Input tokens:  {total_usage.input_tokens:,}")
    print(f"   Output tokens: {total_usage.output_tokens:,}")
    print(f"   Total tokens:  {total_usage.total_tokens:,}")
    print(f"   Est. cost:     ${total_usage.estimated_cost:.4f}")
    
    # Save results
    output_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": MODEL,
        "total_documents": len(results),
        "correct_classifications": sum(1 for r in results if r.match),
        "accuracy_percent": round(sum(1 for r in results if r.match) / len(results) * 100, 1) if results else 0,
        "token_usage": {
            "input_tokens": total_usage.input_tokens,
            "output_tokens": total_usage.output_tokens,
            "total_tokens": total_usage.total_tokens,
            "estimated_cost_usd": round(total_usage.estimated_cost, 4)
        },
        "results": [asdict(r) for r in results]
    }
    
    try:
        with open(RESULTS_FILE, "w") as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Results saved to: {RESULTS_FILE}")
        print(f"\n✅ Results saved to: {RESULTS_FILE}")
        print(f"📝 Log saved to: {log_file}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        print(f"\n⚠️ Warning: Failed to save results: {e}")
    
    print("=" * 60)
    logger.info("Classification pipeline completed")


if __name__ == "__main__":
    main()
