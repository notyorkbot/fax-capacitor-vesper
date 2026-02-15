# Improvement Plan - Fax Capacitor Vesper Build

> **Status:** Actionable improvements derived from independent code review  
> **Priority:** P0 (Critical), P1 (High), P2 (Medium), P3 (Low)  
> **Effort Estimates:** Small (<1hr), Medium (2-4hrs), Large (5-8hrs), XL (>8hrs)

---

## P0: Critical Issues (Fix Immediately)

### 1. Implement Real Image Quality Analysis
**Effort:** Medium (3-4 hours)  
**File:** `scripts/test_classification.py` (lines 96-140)

**Current Problem:**
The "black page detection" at lines 115-117 is completely broken:
```python
if len(img_bytes) < 1000:  # Naive file size check
    pix = page.get_pixmap(matrix=mat, alpha=False)  # Just retries, no analysis
    img_bytes = pix.tobytes("png")
```

Quality scoring (lines 132-140) uses arbitrary file size buckets that have no correlation with actual image quality.

**Implementation Approach:**

```python
import io
from PIL import Image, ImageStat
from typing import Tuple, List

def analyze_image_quality(img_bytes: bytes) -> Tuple[str, bool, float]:
    """
    Analyze image quality using actual pixel metrics.
    
    Returns:
        Tuple of (quality_label, is_mostly_black, brightness_score)
        quality_label: 'good' | 'fair' | 'poor'
        is_mostly_black: True if image is >90% black
        brightness_score: 0-255 mean brightness
    """
    img = Image.open(io.BytesIO(img_bytes))
    
    # Convert to grayscale for analysis
    if img.mode != 'L':
        img_gray = img.convert('L')
    else:
        img_gray = img
    
    # Calculate statistics
    stat = ImageStat.Stat(img_gray)
    mean_brightness = stat.mean[0]
    std_dev = stat.stddev[0]  # Contrast indicator
    
    # Detect black/near-black pages
    is_mostly_black = mean_brightness < 15 and std_dev < 10
    
    # Quality assessment based on contrast and brightness distribution
    if std_dev > 50 and mean_brightness > 30 and mean_brightness < 220:
        quality = "good"  # Good contrast, not over/under-exposed
    elif std_dev > 25:
        quality = "fair"  # Moderate contrast
    else:
        quality = "poor"  # Low contrast (blurry, washed out, or dark)
    
    return quality, is_mostly_black, mean_brightness
```

**Acceptance Criteria:**
- [ ] Function uses actual pixel analysis (PIL/Pillow)
- [ ] Black pages detected by brightness threshold, not file size
- [ ] Quality scored by contrast/brightness distribution, not file size
- [ ] Warning logged when black/low-quality pages detected
- [ ] Unit tests with sample images (black, white, blurry, clear)

**Dependencies:** Add `Pillow` to requirements if not already present.

---

## P1: High Priority Issues (Fix This Week)

### 2. Add API Resilience Layer
**Effort:** Medium (2-3 hours)  
**File:** `scripts/test_classification.py` (lines 157-163)

**Current Problem:** No retry logic, no rate limiting, no exponential backoff. Single API failure = document failure.

**Implementation Approach:**

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from anthropic import RateLimitError, APIError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((RateLimitError, APIError)),
    before_sleep=lambda retry_state: logger.warning(
        f"API call failed (attempt {retry_state.attempt_number}), retrying..."
    )
)
def classify_document_with_retry(images, total_pages, page_quality, client):
    """Classify document with automatic retry on transient failures."""
    return classify_document(images, total_pages, page_quality, client)
```

**Acceptance Criteria:**
- [ ] Retry on RateLimitError with exponential backoff
- [ ] Retry on transient APIError (5xx status codes)
- [ ] Max 3 attempts before giving up
- [ ] Logging of retry attempts
- [ ] Configurable retry count via environment variable

---

### 3. Implement JSON Schema Validation
**Effort:** Medium (3-4 hours)  
**File:** `scripts/test_classification.py` (lines 168-181)

**Current Problem:** Uses `setdefault` which doesn't validate types, ranges, or enum values.

**Implementation Approach:**

```python
from pydantic import BaseModel, Field, validator, ValidationError
from typing import List, Optional, Literal

class ClassificationOutput(BaseModel):
    document_type: Literal[
        "lab_result", "referral_response", "prior_auth_decision",
        "pharmacy_request", "insurance_correspondence", "records_request",
        "marketing_junk", "other"
    ]
    confidence: float = Field(..., ge=0.0, le=1.0)
    priority: Literal["critical", "high", "medium", "low", "none"]
    page_count_processed: int = Field(..., ge=0)
    page_quality: Literal["good", "fair", "poor"]
    flags: List[str] = Field(default_factory=list)
    
    @validator('confidence')
    def enforce_confidence_threshold(cls, v):
        """If confidence below 0.65, document_type should be 'other'."""
        return v
```

**Acceptance Criteria:**
- [ ] Pydantic models for all response fields
- [ ] Type validation for enums (document_type, priority, page_quality)
- [ ] Range validation for confidence (0.0-1.0)
- [ ] Automatic coercion of low-confidence results to "other"
- [ ] Safe fallback on validation failure

**Dependencies:** `pip install pydantic`

---

## P2: Medium Priority (Fix Before Production)

### 4. Add Structured Logging
**Effort:** Small (1-2 hours)  
**File:** `scripts/test_classification.py` (all print statements)

**Implementation Approach:**

```python
import logging
import sys

def setup_logging(level=logging.INFO, log_file=None):
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

logger = logging.getLogger(__name__)

# Replace print() with:
logger.info("Token usage: input=%d, output=%d", input_tokens, output_tokens)
```

**Acceptance Criteria:**
- [ ] All `print()` calls replaced with `logger.info/debug/warning/error`
- [ ] Configurable log level via environment variable
- [ ] Timestamps on all log entries

---

### 5. Add Configuration Management
**Effort:** Small (1-2 hours)  
**New file or inline**

**Current Problem:** Hardcoded constants (lines 18-28).

**Implementation Approach:**

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    anthropic_api_key: str
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024
    temperature: float = 0.0
    dpi: int = 300
    max_pages: int = 3
    test_pdfs_dir: Path = Path("/tmp/fax-capacitor-vesper/data/synthetic-faxes")
    output_dir: Path = Path("/tmp/fax-capacitor-vesper")
    
    class Config:
        env_prefix = "FAX_"
        env_file = ".env"

settings = Settings()
```

**Acceptance Criteria:**
- [ ] All hardcoded constants moved to Settings class
- [ ] Environment variable support with `FAX_` prefix
- [ ] `.env` file support for local development
- [ ] Type validation for all settings

---

## P3: Lower Priority (Nice to Have)

### 6. Add Unit Tests
**Effort:** Large (6-8 hours)  
**New File:** `tests/test_classification.py`

**Test Coverage:**
- Image quality analysis (black page detection, contrast scoring)
- JSON parsing with various malformed inputs
- API retry logic simulation
- Token cost calculation accuracy

**Framework:** `pytest`

---

### 7. Add Parallel Processing
**Effort:** Medium (3-4 hours)  
**File:** `scripts/test_classification.py` (main loop)

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(process_pdf, path): path for path in pdf_files}
    for future in as_completed(futures):
        results.append(future.result())
```

---

### 8. Add Result Caching
**Effort:** Medium (3-4 hours)  
**New File:** `cache.py`

**Purpose:** Avoid re-processing expensive API calls for same documents.

---

## Documentation Improvements

### 9. Rewrite README.md
**Effort:** Medium (3-4 hours)

**Required Sections:**
1. **Quick Start** (5-minute setup)
2. **Prerequisites** (Python 3.11+, dependencies)
3. **Installation** (`pip install -r requirements.txt`)
4. **Configuration** (environment variables, .env file)
5. **Usage** (running the pipeline)
6. **Output Format** (JSON schema documentation)
7. **Architecture** (diagram or description)
8. **Troubleshooting** (common errors)

---

### 10. Add Requirements.txt
**Effort:** Small (< 1 hour)  
**New File:** `requirements.txt`

```
anthropic>=0.21.0
PyMuPDF>=1.23.0
Pillow>=10.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
tenacity>=8.0.0
```

---

## Summary Table

| Priority | Improvement | Effort | Impact |
|----------|-------------|--------|--------|
| P0 | Real image quality analysis | Medium | 🔴 Critical |
| P1 | API resilience layer | Medium | 🟠 High |
| P1 | JSON schema validation | Medium | 🟠 High |
| P2 | Structured logging | Small | 🟡 Medium |
| P2 | Configuration management | Small | 🟡 Medium |
| P3 | Unit tests | Large | 🟢 Low (for demo) |
| P3 | Parallel processing | Medium | 🟢 Low |
| P3 | Result caching | Medium | 🟢 Low |
| - | Documentation rewrite | Medium | 🟡 Medium |
| - | Requirements.txt | Small | 🟢 Low |

**Recommended MVP for Interview Demo:**
Fix P0 + P1 items (image quality, API resilience, JSON validation). This gets the code from "prototype" to "production-ready demo" status.
