"""Validation Framework for Fax Classification Pipeline

Compares classification results to expected outcomes, calculates accuracy metrics,
generates comparison reports, and tracks edge cases.
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime

# Expected classifications from test_classification.py
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

# Edge case definitions with descriptions
EDGE_CASES = {
    "09_orphan_cover_page.pdf": {
        "type": "orphan_cover_page",
        "description": "Fax cover sheet with no attached content pages",
        "challenge": "Classifier must detect incomplete document",
        "expected": "other",
        "flags_expected": ["incomplete_document"]
    },
    "10_chart_dump_40pages.pdf": {
        "type": "multi_document_bundle",
        "description": "40-page patient chart containing multiple document types",
        "challenge": "Classifier must detect multi-type bundle",
        "expected": "other",
        "flags_expected": ["multi_document_bundle"]
    },
    "12_wrong_provider_misdirected.pdf": {
        "type": "misdirected",
        "description": "Fax clearly addressed to different provider/practice",
        "challenge": "Classifier must detect wrong recipient",
        "expected": "other",
        "flags_expected": ["possibly_misdirected"]
    }
}


@dataclass
class ValidationResult:
    """Result of validating a single classification."""
    filename: str
    expected: str
    actual: str
    is_edge_case: bool
    edge_case_type: Optional[str]
    correct: bool
    confidence: float
    priority: str
    flags: List[str]
    notes: Optional[str] = None


@dataclass
class AccuracyMetrics:
    """Overall accuracy metrics."""
    total_documents: int
    correct_classifications: int
    accuracy_percent: float
    edge_cases_total: int
    edge_cases_correct: int
    edge_case_accuracy: float
    standard_cases_total: int
    standard_cases_correct: int
    standard_case_accuracy: float


class ClassificationValidator:
    """Validates classification results against expected outcomes."""
    
    def __init__(self, expected: Dict[str, str] = None):
        self.expected = expected or EXPECTED_CLASSIFICATIONS
        self.edge_cases = EDGE_CASES
        self.results: List[ValidationResult] = []
    
    def validate_result(self, filename: str, actual_classification: str, 
                        confidence: float = 0.0, priority: str = "none",
                        flags: List[str] = None, notes: str = None) -> ValidationResult:
        """Validate a single classification result."""
        flags = flags or []
        
        expected = self.expected.get(filename)
        if expected is None:
            raise ValueError(f"No expected classification for {filename}")
        
        is_edge_case = filename in self.edge_cases
        edge_case_type = self.edge_cases.get(filename, {}).get("type") if is_edge_case else None
        
        result = ValidationResult(
            filename=filename,
            expected=expected,
            actual=actual_classification,
            is_edge_case=is_edge_case,
            edge_case_type=edge_case_type,
            correct=(actual_classification == expected),
            confidence=confidence,
            priority=priority,
            flags=flags,
            notes=notes
        )
        
        self.results.append(result)
        return result
    
    def validate_json_results(self, results_json: List[Dict]) -> List[ValidationResult]:
        """Validate multiple results from JSON output."""
        validated = []
        
        for result in results_json:
            filename = result.get("filename")
            if not filename:
                continue
                
            validated_result = self.validate_result(
                filename=filename,
                actual_classification=result.get("actual", "unknown"),
                confidence=result.get("confidence", 0.0),
                priority=result.get("priority", "none"),
                flags=result.get("flags", []),
                notes=result.get("error")
            )
            validated.append(validated_result)
        
        return validated
    
    def calculate_metrics(self) -> AccuracyMetrics:
        """Calculate accuracy metrics."""
        if not self.results:
            return AccuracyMetrics(0, 0, 0.0, 0, 0, 0.0, 0, 0, 0.0)
        
        total = len(self.results)
        correct = sum(1 for r in self.results if r.correct)
        
        edge_case_results = [r for r in self.results if r.is_edge_case]
        standard_results = [r for r in self.results if not r.is_edge_case]
        
        edge_total = len(edge_case_results)
        edge_correct = sum(1 for r in edge_case_results if r.correct)
        
        standard_total = len(standard_results)
        standard_correct = sum(1 for r in standard_results if r.correct)
        
        return AccuracyMetrics(
            total_documents=total,
            correct_classifications=correct,
            accuracy_percent=(correct / total * 100) if total > 0 else 0.0,
            edge_cases_total=edge_total,
            edge_cases_correct=edge_correct,
            edge_case_accuracy=(edge_correct / edge_total * 100) if edge_total > 0 else 0.0,
            standard_cases_total=standard_total,
            standard_cases_correct=standard_correct,
            standard_case_accuracy=(standard_correct / standard_total * 100) if standard_total > 0 else 0.0
        )
    
    def get_misclassifications(self) -> List[ValidationResult]:
        """Get all misclassified documents."""
        return [r for r in self.results if not r.correct]
    
    def get_edge_case_results(self) -> List[ValidationResult]:
        """Get all edge case results."""
        return [r for r in self.results if r.is_edge_case]
    
    def generate_comparison_table(self) -> str:
        """Generate a formatted comparison table."""
        lines = []
        lines.append("=" * 130)
        lines.append(f"{'Filename':<40} {'Expected':<20} {'Actual':<20} {'Match':<6} {'Conf':<6} {'Edge Case':<12} {'Flags'}")
        lines.append("-" * 130)
        
        for r in sorted(self.results, key=lambda x: x.filename):
            match_str = "✓" if r.correct else "✗"
            edge_str = r.edge_case_type if r.is_edge_case else "-"
            flags_str = ", ".join(r.flags[:2]) if r.flags else "-"
            lines.append(
                f"{r.filename:<40} {r.expected:<20} {r.actual:<20} {match_str:<6} "
                f"{r.confidence:<6.2f} {edge_str:<12} {flags_str}"
            )
        
        lines.append("-" * 130)
        return "\n".join(lines)
    
    def generate_report(self) -> Dict:
        """Generate a comprehensive validation report."""
        metrics = self.calculate_metrics()
        misclassifications = self.get_misclassifications()
        edge_cases = self.get_edge_case_results()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_documents": metrics.total_documents,
                "correct_classifications": metrics.correct_classifications,
                "accuracy_percent": round(metrics.accuracy_percent, 1),
                "edge_cases": {
                    "total": metrics.edge_cases_total,
                    "correct": metrics.edge_cases_correct,
                    "accuracy_percent": round(metrics.edge_case_accuracy, 1)
                },
                "standard_cases": {
                    "total": metrics.standard_cases_total,
                    "correct": metrics.standard_cases_correct,
                    "accuracy_percent": round(metrics.standard_case_accuracy, 1)
                }
            },
            "misclassifications": [
                {
                    "filename": r.filename,
                    "expected": r.expected,
                    "actual": r.actual,
                    "is_edge_case": r.is_edge_case,
                    "edge_case_type": r.edge_case_type,
                    "confidence": r.confidence,
                    "flags": r.flags
                }
                for r in misclassifications
            ],
            "edge_case_details": [
                {
                    "filename": r.filename,
                    "type": r.edge_case_type,
                    "expected": r.expected,
                    "actual": r.actual,
                    "correct": r.correct,
                    "confidence": r.confidence,
                    "flags": r.flags,
                    "description": self.edge_cases.get(r.filename, {}).get("description"),
                    "challenge": self.edge_cases.get(r.filename, {}).get("challenge")
                }
                for r in edge_cases
            ],
            "all_results": [asdict(r) for r in self.results]
        }
        
        return report
    
    def save_report(self, output_path: Path):
        """Save validation report to JSON file."""
        report = self.generate_report()
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
    
    def print_summary(self):
        """Print summary to console."""
        metrics = self.calculate_metrics()
        
        print("\n" + "=" * 60)
        print("CLASSIFICATION VALIDATION SUMMARY")
        print("=" * 60)
        print(f"\nTotal Documents: {metrics.total_documents}")
        print(f"Correct: {metrics.correct_classifications}")
        print(f"Accuracy: {metrics.accuracy_percent:.1f}%")
        print(f"\nEdge Cases:")
        print(f"  Total: {metrics.edge_cases_total}")
        print(f"  Correct: {metrics.edge_cases_correct}")
        print(f"  Accuracy: {metrics.edge_case_accuracy:.1f}%")
        print(f"\nStandard Cases:")
        print(f"  Total: {metrics.standard_cases_total}")
        print(f"  Correct: {metrics.standard_cases_correct}")
        print(f"  Accuracy: {metrics.standard_case_accuracy:.1f}%")
        
        misclassifications = self.get_misclassifications()
        if misclassifications:
            print(f"\n⚠ Misclassifications ({len(misclassifications)}):")
            for m in misclassifications:
                edge_note = f" [{m.edge_case_type}]" if m.is_edge_case else ""
                print(f"  - {m.filename}: expected '{m.expected}', got '{m.actual}'{edge_note}")
        
        print("\n" + "=" * 60)


def load_results_from_file(results_path: Path) -> List[Dict]:
    """Load classification results from JSON file."""
    with open(results_path, 'r') as f:
        data = json.load(f)
    
    # Handle both direct results list and wrapped format
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "results" in data:
        return data["results"]
    else:
        raise ValueError(f"Unexpected results file format: {results_path}")


def main():
    """Main entry point for validation runner."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate classification results against expected outcomes"
    )
    parser.add_argument(
        "results_file",
        type=Path,
        nargs="?",
        default=Path("/tmp/fax-capacitor-vesper/phase1_validation_results.json"),
        help="Path to classification results JSON file"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("/tmp/fax-capacitor-vesper/validation_report.json"),
        help="Output path for validation report"
    )
    parser.add_argument(
        "--table",
        action="store_true",
        help="Print detailed comparison table"
    )
    
    args = parser.parse_args()
    
    # Load results
    try:
        results = load_results_from_file(args.results_file)
        print(f"✓ Loaded {len(results)} results from {args.results_file}")
    except FileNotFoundError:
        print(f"❌ Results file not found: {args.results_file}")
        print("Run test_classification.py first to generate results")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading results: {e}")
        sys.exit(1)
    
    # Validate
    validator = ClassificationValidator()
    validator.validate_json_results(results)
    
    # Print comparison table if requested
    if args.table:
        print("\n" + validator.generate_comparison_table())
    
    # Print summary
    validator.print_summary()
    
    # Save report
    validator.save_report(args.output)
    print(f"\n✓ Validation report saved to: {args.output}")


if __name__ == "__main__":
    main()