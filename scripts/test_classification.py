#!/usr/bin/env python3
"""FaxTriage AI Classification Pipeline - Agent-1 Implementation"""

import os
import sys
import json
import base64
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

import fitz
from anthropic import Anthropic

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

CLASSIFICATION_PROMPT = """You are a medical document classification system for Whispering Pines Family Medicine (fax: 555-867-5309, provider: Dr. Evelyn Sato, DO). You analyze fax documents received as images and return structured classification data.

## Task
Analyze the provided fax document image(s) and:
1. Classify the document type
2. Extract key metadata fields
3. Assess priority level
4. Provide a confidence score for your classification

## Document Types
Classify into exactly ONE of the following types:
- lab_result: Blood work, pathology, imaging reports, urinalysis results
- referral_response: Specialist consultation notes, referral acknowledgments, appointment confirmations, consult reports sent back to the referring provider
- prior_auth_decision: Insurance approval, denial, or pending notices for procedures/medications/referrals
- pharmacy_request: Refill requests, formulary changes, prior auth for medications, drug interaction alerts
- insurance_correspondence: EOBs, coverage changes, claim correspondence, eligibility updates, coordination of benefits requests
- records_request: Medical records requests from other providers, attorneys, insurance companies, or patients
- marketing_junk: Vendor solicitations, equipment sales, supply catalogs, unsolicited advertisements, EHR sales pitches
- other: Anything not clearly matching the above categories, including: orphan cover pages without attached content, misdirected faxes intended for a different recipient, multi-type document bundles that don't fit a single category, or documents too illegible to classify

## Priority Levels
- critical: Critical lab values, prior auth denials near appeal deadline, STAT results
- high: Lab results with abnormal values, prior auth decisions (especially denials)
- medium: Referral responses, pharmacy requests, records requests
- low: Insurance correspondence, routine items, informational documents
- none: Marketing/junk

## Urgency Indicators
Flag any of the following if present: "CRITICAL VALUE", "STAT", "URGENT", "DENIED", "APPEAL DEADLINE", "ABNORMAL", "PANIC VALUE", specific deadline dates, "time-sensitive"

## Misdirected Fax Detection
If the document is clearly addressed to a different provider/practice (not Whispering Pines Family Medicine or Dr. Sato), flag it as possibly misdirected. This includes documents where the TO: line names a different practice or the content is clearly intended for another provider. A document CAN be relevant to our practice even if sent FROM another provider — what matters is whether it's intended FOR us.

## Output Format
Respond with ONLY a JSON object (no markdown, no explanation, no code fences):

{
  "document_type": "string (one of the types listed above)",
  "confidence": number (0.0 to 1.0),
  "priority": "string (critical/high/medium/low/none)",
  "extracted_fields": {
    "patient_name": "string or null",
    "patient_dob": "string (YYYY-MM-DD) or null",
    "sending_provider": "string or null",
    "sending_facility": "string or null",
    "document_date": "string (YYYY-MM-DD) or null",
    "fax_origin_number": "string or null",
    "urgency_indicators": ["array of strings"] or [],
    "key_details": "string - brief summary of the document's key content"
  },
  "is_continuation": false,
  "page_count_processed": number,
  "page_quality": "string (good/fair/poor)",
  "flags": ["array of any notable issues — include 'possibly_misdirected' if applicable, 'incomplete_document' if pages appear missing, 'multi_document_bundle' if fax contains multiple distinct document types"]
}

## Rules
- If you cannot determine a field, set it to null — do not guess
- If confidence is below 0.65, set document_type to "other" regardless of your best guess
- For marketing/junk, you do not need to extract patient fields
- If the document appears to be a cover sheet followed by content, classify based on the content type described in the cover sheet
- If the document is ONLY a cover sheet with no attached content, classify as "other" and flag as "incomplete_document"
- Be conservative with critical/high priority — only assign when urgency indicators are clearly present
- If multiple pages are provided, base classification on the overall document, not individual pages"""


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


def pdf_to_base64_images(pdf_path: Path):
    """Convert PDF pages to base64 PNG images at specified DPI."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    pages_to_process = min(total_pages, MAX_PAGES) if total_pages > 5 else total_pages
    
    images = []
    qualities = []
    
    for page_num in range(pages_to_process):
        page = doc[page_num]
        zoom = DPI / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        
        if len(img_bytes) < 1000:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")
        
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        images.append(b64)
        
        if len(img_bytes) > 500_000:
            qualities.append("good")
        elif len(img_bytes) > 100_000:
            qualities.append("fair")
        else:
            qualities.append("poor")
    
    doc.close()
    
    if all(q == "good" for q in qualities):
        overall_quality = "good"
    elif any(q == "poor" for q in qualities):
        overall_quality = "poor"
    else:
        overall_quality = "fair"
    
    return images, total_pages, overall_quality


def classify_document(images, total_pages, page_quality, client):
    """Send images to Claude Vision API for classification."""
    content = [{"type": "text", "text": CLASSIFICATION_PROMPT}]
    
    for img_b64 in images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": img_b64
            }
        })
    
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": content}]
    )
    
    try:
        result_text = response.content[0].text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        result = json.loads(result_text)
        result.setdefault("document_type", "other")
        result.setdefault("confidence", 0.0)
        result.setdefault("priority", "none")
        result.setdefault("extracted_fields", {})
        result.setdefault("flags", [])
        result["page_count_processed"] = len(images)
        result["page_quality"] = page_quality
        
    except json.JSONDecodeError as e:
        result_text_local = result_text if 'result_text' in dir() else ""
        result = {
            "document_type": "other",
            "confidence": 0.0,
            "priority": "none",
            "extracted_fields": {},
            "flags": ["json_parse_error"],
            "page_count_processed": len(images),
            "page_quality": page_quality,
            "parse_error": str(e),
            "raw_response": result_text_local[:500]
        }
    
    usage = TokenUsage(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens
    )
    
    return result, usage


def print_summary_table(results):
    """Print a formatted summary table of classification results."""
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
    """Main classification pipeline."""
    print("=" * 60)
    print("FaxTriage AI Classification Pipeline - Agent-1")
    print("=" * 60)
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)
    
    client = Anthropic(api_key=api_key)
    
    pdf_files = sorted([f for f in TEST_PDFS_DIR.iterdir() if f.suffix.lower() == ".pdf"])
    if not pdf_files:
        print(f"❌ No PDF files found in {TEST_PDFS_DIR}")
        sys.exit(1)
    
    print(f"\n📄 Found {len(pdf_files)} PDF files to process")
    print(f"🔑 Using model: {MODEL}")
    print(f"📊 DPI: {DPI}, Max pages per doc: {MAX_PAGES}")
    print()
    
    results = []
    total_usage = TokenUsage()
    
    for i, pdf_path in enumerate(pdf_files, 1):
        filename = pdf_path.name
        expected = EXPECTED_CLASSIFICATIONS.get(filename, "unknown")
        
        print(f"[{i}/{len(pdf_files)}] Processing {filename}...", end=" ", flush=True)
        start_time = time.time()
        
        try:
            images, total_pages, page_quality = pdf_to_base64_images(pdf_path)
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
            
        except Exception as e:
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
        
        results.append(result)
    
    print_summary_table(results)
    
    print(f"\n📊 Token Usage:")
    print(f"   Input tokens:  {total_usage.input_tokens:,}")
    print(f"   Output tokens: {total_usage.output_tokens:,}")
    print(f"   Total tokens:  {total_usage.total_tokens:,}")
    print(f"   Est. cost:     ${total_usage.estimated_cost:.4f}")
    
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
    
    with open(RESULTS_FILE, "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✅ Results saved to: {RESULTS_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
