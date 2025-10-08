#!/usr/bin/env python3
"""
Example usage of the transcript validation module.

This script demonstrates how to use the transcript validation functionality
to analyze existing transcript outputs for quality issues.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models import TranscriptionConfig
from core.pipeline import TranscriptionPipeline
from core.validation import TranscriptValidator


def validate_existing_transcript():
    """Example of validating an existing transcript file."""
    print("=== Validating Existing Transcript ===")
    
    # Path to an existing clean transcript
    transcript_path = "outputs/pipeline_runs/transcription_run_20251007_142250/transcripts/Adam_2024-03-03_6_32_PM_615cb15d_clean_transcript.json"
    
    if not Path(transcript_path).exists():
        print(f"Transcript file not found: {transcript_path}")
        print("Please run a transcription pipeline first to generate a transcript.")
        return
    
    # Create validator with custom gap threshold
    validator = TranscriptValidator(gap_threshold_seconds=5.0)  # 5 second gap threshold
    
    # Validate the transcript
    print(f"Validating transcript: {transcript_path}")
    validation_results = validator.validate_clean_transcript(transcript_path)
    
    # Generate and save reports
    report_path = Path(transcript_path).parent / "validation_report.txt"
    validator.generate_validation_report(validation_results, report_path)
    
    # Generate detailed JSON report
    json_report_path = Path(transcript_path).parent / "validation_detailed.json"
    detailed_report = validator.generate_detailed_json_report(validation_results, json_report_path)
    
    # Print summary
    summary = validation_results.get_summary()
    print(f"\nValidation Summary:")
    print(f"  - Passed: {'✓' if summary['validation_passed'] else '✗'}")
    print(f"  - Total Issues: {summary['total_issues']}")
    print(f"  - Errors: {summary['errors']}, Warnings: {summary['warnings']}, Info: {summary['info']}")
    print(f"  - Gaps: {summary['gaps_found']}, Failed Chunks: {summary['failed_chunks']}, Overlaps: {summary['overlaps_found']}")
    print(f"  - Chronological Order: {'✓' if summary['chronological_order_valid'] else '✗'}")
    print(f"  - Text report: {report_path}")
    print(f"  - Detailed JSON: {json_report_path}")
    
    # Show example of detailed issue data
    if detailed_report['detailed_issues']:
        first_issue_type = detailed_report['detailed_issues'][0]
        if first_issue_type['issues']:
            first_issue = first_issue_type['issues'][0]
            print(f"\nExample detailed issue data:")
            print(f"  - Issue Type: {first_issue['issue_type']}")
            print(f"  - Severity: {first_issue['severity']}")
            print(f"  - Description: {first_issue['description']}")
            if 'entry_data' in first_issue:
                print(f"  - Entry Data Available: ✓")
                if 'current_entry' in first_issue['entry_data']:
                    entry = first_issue['entry_data']['current_entry']
                    print(f"    - Current Entry: {entry.get('text', 'N/A')[:50]}...")
                if 'previous_entry' in first_issue['entry_data']:
                    entry = first_issue['entry_data']['previous_entry']
                    print(f"    - Previous Entry: {entry.get('text', 'N/A')[:50]}...")


def validate_with_pipeline():
    """Example of using validation with the pipeline."""
    print("\n=== Using Validation with Pipeline ===")
    
    # Create pipeline with validation enabled
    pipeline = TranscriptionPipeline(
        base_dir="outputs",
        data_dir="data",
        enable_file_management=True,
        enable_video_repository=True,
        enable_validation=True,
        gap_threshold_seconds=10.0  # 10 second gap threshold
    )
    
    # Example video path (adjust as needed)
    video_path = "data/videos/Adam_2024-03-03_6_32_PM.mp4"
    
    if not Path(video_path).exists():
        print(f"Video file not found: {video_path}")
        print("Please ensure you have a video file to process.")
        return
    
    # Create configuration
    config = TranscriptionConfig(
        video_input=video_path,
        chunk_duration=300,
        max_workers=2,
        force_reprocess=False  # Use cached if available
    )
    
    try:
        # Process video with validation
        print(f"Processing video: {video_path}")
        results = pipeline.process_video(config)
        
        print(f"\nPipeline completed successfully!")
        print(f"Results saved to: {pipeline.run_dir}")
        
        # The validation results are automatically generated during processing
        # Check the logs directory for the validation report
        
    except Exception as e:
        print(f"Error processing video: {e}")
    
    finally:
        # Clean up
        pipeline.cleanup()


def validate_multiple_transcripts():
    """Example of validating multiple transcript files."""
    print("\n=== Validating Multiple Transcripts ===")
    
    # Find all clean transcript files
    outputs_dir = Path("outputs/pipeline_runs")
    transcript_files = []
    
    if outputs_dir.exists():
        for run_dir in outputs_dir.iterdir():
            if run_dir.is_dir():
                transcripts_dir = run_dir / "transcripts"
                if transcripts_dir.exists():
                    for transcript_file in transcripts_dir.glob("*_clean_transcript.json"):
                        transcript_files.append(transcript_file)
    
    if not transcript_files:
        print("No clean transcript files found.")
        return
    
    print(f"Found {len(transcript_files)} transcript files to validate:")
    
    # Create validator
    validator = TranscriptValidator(gap_threshold_seconds=10.0)
    
    # Validate each transcript
    for i, transcript_path in enumerate(transcript_files, 1):
        print(f"\n{i}. Validating: {transcript_path.name}")
        
        try:
            validation_results = validator.validate_clean_transcript(transcript_path)
            summary = validation_results.get_summary()
            
            print(f"   - Passed: {'✓' if summary['validation_passed'] else '✗'}")
            print(f"   - Issues: {summary['total_issues']} (E:{summary['errors']}, W:{summary['warnings']}, I:{summary['info']})")
            print(f"   - Gaps: {summary['gaps_found']}, Failed: {summary['failed_chunks']}, Overlaps: {summary['overlaps_found']}")
            
            # Generate report
            report_path = transcript_path.parent / f"{transcript_path.stem}_validation_report.txt"
            validator.generate_validation_report(validation_results, report_path)
            print(f"   - Report: {report_path}")
            
        except Exception as e:
            print(f"   - Error validating: {e}")


def main():
    """Main function to run validation examples."""
    print("Transcript Validation Examples")
    print("=" * 50)
    
    # Example 1: Validate existing transcript
    validate_existing_transcript()
    
    # Example 2: Use validation with pipeline (commented out to avoid processing)
    # validate_with_pipeline()
    
    # Example 3: Validate multiple transcripts
    validate_multiple_transcripts()
    
    print("\nValidation examples completed!")


if __name__ == "__main__":
    main()
