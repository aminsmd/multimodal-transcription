#!/usr/bin/env python3
"""
Standalone script for validating transcript files.

Usage:
    python validate_transcript.py <transcript_path> [gap_threshold_seconds]
    
Example:
    python validate_transcript.py outputs/pipeline_runs/transcription_run_20251007_142250/transcripts/Adam_2024-03-03_6_32_PM_615cb15d_clean_transcript.json 10
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.validation import TranscriptValidator


def main():
    """Main function for standalone transcript validation."""
    parser = argparse.ArgumentParser(description="Validate transcript files for quality issues")
    parser.add_argument("transcript_path", help="Path to the clean transcript JSON file")
    parser.add_argument("gap_threshold", type=float, nargs="?", default=10.0, 
                       help="Gap threshold in seconds (default: 10.0)")
    parser.add_argument("--output", "-o", help="Output path for validation report")
    
    args = parser.parse_args()
    
    # Check if transcript file exists
    transcript_path = Path(args.transcript_path)
    if not transcript_path.exists():
        print(f"Error: Transcript file not found: {transcript_path}")
        sys.exit(1)
    
    # Create validator
    validator = TranscriptValidator(gap_threshold_seconds=args.gap_threshold)
    
    print(f"Validating transcript: {transcript_path}")
    print(f"Gap threshold: {args.gap_threshold} seconds")
    print("-" * 50)
    
    try:
        # Validate the transcript
        validation_results = validator.validate_clean_transcript(transcript_path)
        
        # Determine output path
        if args.output:
            report_path = Path(args.output)
        else:
            report_path = transcript_path.parent / f"{transcript_path.stem}_validation_report.txt"
        
        # Generate reports
        validator.generate_validation_report(validation_results, report_path)
        
        # Generate detailed JSON report
        json_report_path = transcript_path.parent / f"{transcript_path.stem}_validation_detailed.json"
        validator.generate_detailed_json_report(validation_results, json_report_path)
        
        # Print summary
        summary = validation_results.get_summary()
        print(f"\nValidation Results:")
        print(f"  - Passed: {'✓' if summary['validation_passed'] else '✗'}")
        print(f"  - Total Issues: {summary['total_issues']}")
        print(f"  - Errors: {summary['errors']}, Warnings: {summary['warnings']}, Info: {summary['info']}")
        print(f"  - Gaps: {summary['gaps_found']}, Failed Chunks: {summary['failed_chunks']}, Overlaps: {summary['overlaps_found']}")
        print(f"  - Chronological Order: {'✓' if summary['chronological_order_valid'] else '✗'}")
        print(f"  - Text report: {report_path}")
        print(f"  - Detailed JSON: {json_report_path}")
        
        # Exit with appropriate code
        sys.exit(0 if summary['validation_passed'] else 1)
        
    except Exception as e:
        print(f"Error validating transcript: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
