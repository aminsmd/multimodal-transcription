#!/usr/bin/env python3
"""
Transcript validation module for analyzing transcription outputs.

This module provides comprehensive validation of transcript outputs including:
- Chronological order verification (within entry types)
- Gap detection with configurable thresholds
- Failed chunk identification
- Overlap detection (within same entry types only)

Note: Event and utterance entries can overlap in time (they represent different
aspects of the same time period), but entries of the same type should not overlap.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import CleanTranscript, CleanTranscriptEntry, ValidationResults, ValidationIssue


class TranscriptValidator:
    """
    Validates transcript outputs for various quality issues.
    
    This class provides comprehensive validation of transcript outputs,
    checking for chronological order, gaps, overlaps, and failed chunks.
    
    Important: Event and utterance entries can overlap in time (they represent
    different aspects of the same time period), but entries of the same type
    should not overlap with each other.
    """
    
    def __init__(self, gap_threshold_seconds: float = 10.0):
        """
        Initialize the transcript validator.
        
        Args:
            gap_threshold_seconds: Minimum gap duration to report as an issue
        """
        self.gap_threshold_seconds = gap_threshold_seconds
    
    def validate_clean_transcript(self, transcript_path: Union[str, Path]) -> ValidationResults:
        """
        Validate a clean transcript JSON file.
        
        Args:
            transcript_path: Path to the clean transcript JSON file
            
        Returns:
            ValidationResults: Comprehensive validation results
        """
        transcript_path = Path(transcript_path)
        
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {transcript_path}")
        
        # Load transcript data
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        # Create CleanTranscript object
        clean_transcript = CleanTranscript.from_dict(transcript_data)
        
        return self.validate_transcript_object(clean_transcript)
    
    def validate_transcript_object(self, transcript: CleanTranscript) -> ValidationResults:
        """
        Validate a CleanTranscript object.
        
        Args:
            transcript: CleanTranscript object to validate
            
        Returns:
            ValidationResults: Comprehensive validation results
        """
        issues = []
        
        # Convert time strings to seconds for analysis
        entries_with_times = self._parse_transcript_entries(transcript.transcript)
        
        # Check chronological order
        chronological_issues = self._check_chronological_order(entries_with_times)
        issues.extend(chronological_issues)
        
        # Check for gaps
        gap_issues = self._check_gaps(entries_with_times, transcript.duration_seconds)
        issues.extend(gap_issues)
        
        # Check for overlaps
        overlap_issues = self._check_overlaps(entries_with_times)
        issues.extend(overlap_issues)
        
        # Check for failed chunks (empty or very short entries)
        failed_chunk_issues = self._check_failed_chunks(entries_with_times)
        issues.extend(failed_chunk_issues)
        
        # Determine if validation passed
        error_count = sum(1 for issue in issues if issue.severity == 'error')
        validation_passed = error_count == 0
        
        # Count specific issue types
        gaps_found = len([issue for issue in issues if issue.issue_type == 'gap'])
        overlaps_found = len([issue for issue in issues if issue.issue_type == 'overlap'])
        failed_chunks = [issue.chunk_index for issue in issues if issue.issue_type == 'failed_chunk' and issue.chunk_index is not None]
        
        chronological_order_valid = len([issue for issue in issues if issue.issue_type == 'chronological_order']) == 0
        
        return ValidationResults(
            video_id=transcript.video_id,
            validation_date=datetime.now().isoformat(),
            total_entries=len(transcript.transcript),
            total_duration_seconds=transcript.duration_seconds,
            issues=issues,
            chronological_order_valid=chronological_order_valid,
            gap_threshold_seconds=self.gap_threshold_seconds,
            gaps_found=gaps_found,
            failed_chunks=failed_chunks,
            overlaps_found=overlaps_found,
            validation_passed=validation_passed
        )
    
    def _parse_transcript_entries(self, transcript: List[CleanTranscriptEntry]) -> List[Dict]:
        """
        Parse transcript entries and convert time strings to seconds.
        
        Args:
            transcript: List of CleanTranscriptEntry objects
            
        Returns:
            List of dictionaries with parsed timing information
        """
        entries_with_times = []
        
        for i, entry in enumerate(transcript):
            start_seconds = self._time_string_to_seconds(entry.start_time)
            end_seconds = self._time_string_to_seconds(entry.end_time)
            
            entries_with_times.append({
                'index': i,
                'entry': entry,
                'start_seconds': start_seconds,
                'end_seconds': end_seconds,
                'duration': end_seconds - start_seconds if end_seconds > start_seconds else 0
            })
        
        return entries_with_times
    
    def _time_string_to_seconds(self, time_str: str) -> float:
        """
        Convert time string (MM:SS or HH:MM:SS) to seconds.
        
        Args:
            time_str: Time string in format MM:SS or HH:MM:SS
            
        Returns:
            Time in seconds as float
        """
        if not time_str:
            return 0.0
        
        # Handle different time formats
        time_parts = time_str.split(':')
        
        if len(time_parts) == 2:  # MM:SS
            minutes, seconds = time_parts
            return float(minutes) * 60 + float(seconds)
        elif len(time_parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = time_parts
            return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
        else:
            # Try to parse as float directly
            try:
                return float(time_str)
            except ValueError:
                return 0.0
    
    def _check_chronological_order(self, entries: List[Dict]) -> List[ValidationIssue]:
        """
        Check if transcript entries are in chronological order.
        
        Note: We check chronological order within each type separately, as event and
        utterance entries can have different timing patterns.
        
        Args:
            entries: List of parsed transcript entries
            
        Returns:
            List of ValidationIssue objects for chronological order problems
        """
        issues = []
        
        # Group entries by type
        event_entries = [entry for entry in entries if entry['entry'].type == 'event']
        utterance_entries = [entry for entry in entries if entry['entry'].type == 'utterance']
        
        # Check chronological order within event entries
        event_issues = self._check_chronological_order_within_type(event_entries, 'event')
        issues.extend(event_issues)
        
        # Check chronological order within utterance entries
        utterance_issues = self._check_chronological_order_within_type(utterance_entries, 'utterance')
        issues.extend(utterance_issues)
        
        return issues
    
    def _check_chronological_order_within_type(self, entries: List[Dict], entry_type: str) -> List[ValidationIssue]:
        """
        Check chronological order within entries of the same type.
        
        Args:
            entries: List of parsed transcript entries of the same type
            entry_type: Type of entries being checked ('event' or 'utterance')
            
        Returns:
            List of ValidationIssue objects for chronological order problems
        """
        issues = []
        
        if len(entries) < 2:
            return issues
        
        # Sort entries by start time
        sorted_entries = sorted(entries, key=lambda x: x['start_seconds'])
        
        for i in range(1, len(sorted_entries)):
            prev_entry = sorted_entries[i-1]
            curr_entry = sorted_entries[i]
            
            # Check if current entry starts before previous entry ends
            if curr_entry['start_seconds'] < prev_entry['end_seconds']:
                # This might be an overlap, but let's also check if it's out of order
                if curr_entry['start_seconds'] < prev_entry['start_seconds']:
                    issues.append(ValidationIssue(
                    issue_type='chronological_order',
                    severity='error',
                    start_time=curr_entry['start_seconds'],
                    end_time=curr_entry['end_seconds'],
                    description=f"{entry_type.capitalize()} entry {curr_entry['index']} starts before previous entry ends. "
                              f"Current: {curr_entry['entry'].start_time}, "
                              f"Previous end: {prev_entry['entry'].end_time}",
                    entry_index=curr_entry['index'],
                    entry_data={
                        'current_entry': curr_entry['entry'].to_dict(),
                        'previous_entry': prev_entry['entry'].to_dict()
                    }
                ))
        
        return issues
    
    def _check_gaps(self, entries: List[Dict], total_duration: float) -> List[ValidationIssue]:
        """
        Check for gaps in the transcript that exceed the threshold.
        
        Args:
            entries: List of parsed transcript entries
            total_duration: Total duration of the video in seconds
            
        Returns:
            List of ValidationIssue objects for gaps found
        """
        issues = []
        
        if not entries:
            return issues
        
        # Sort entries by start time to ensure proper gap detection
        sorted_entries = sorted(entries, key=lambda x: x['start_seconds'])
        
        # Check for gap at the beginning
        if sorted_entries[0]['start_seconds'] > self.gap_threshold_seconds:
            issues.append(ValidationIssue(
                issue_type='gap',
                severity='warning',
                start_time=0.0,
                end_time=sorted_entries[0]['start_seconds'],
                description=f"Gap at beginning of transcript: {sorted_entries[0]['start_seconds']:.2f} seconds",
                entry_index=0,
                entry_data={
                    'gap_duration': sorted_entries[0]['start_seconds'],
                    'next_entry': sorted_entries[0]['entry'].to_dict()
                }
            ))
        
        # Check for gaps between entries
        for i in range(1, len(sorted_entries)):
            prev_entry = sorted_entries[i-1]
            curr_entry = sorted_entries[i]
            
            gap_duration = curr_entry['start_seconds'] - prev_entry['end_seconds']
            
            if gap_duration > self.gap_threshold_seconds:
                issues.append(ValidationIssue(
                    issue_type='gap',
                    severity='warning',
                    start_time=prev_entry['end_seconds'],
                    end_time=curr_entry['start_seconds'],
                    description=f"Gap between entries: {gap_duration:.2f} seconds "
                              f"(from {prev_entry['entry'].end_time} to {curr_entry['entry'].start_time})",
                    entry_index=curr_entry['index'],
                    entry_data={
                        'gap_duration': gap_duration,
                        'previous_entry': prev_entry['entry'].to_dict(),
                        'next_entry': curr_entry['entry'].to_dict()
                    }
                ))
        
        # Check for gap at the end
        last_entry = sorted_entries[-1]
        end_gap = total_duration - last_entry['end_seconds']
        if end_gap > self.gap_threshold_seconds:
            issues.append(ValidationIssue(
                issue_type='gap',
                severity='warning',
                start_time=last_entry['end_seconds'],
                end_time=total_duration,
                description=f"Gap at end of transcript: {end_gap:.2f} seconds",
                entry_index=len(entries) - 1,
                entry_data={
                    'gap_duration': end_gap,
                    'last_entry': last_entry['entry'].to_dict()
                }
            ))
        
        return issues
    
    def _check_overlaps(self, entries: List[Dict]) -> List[ValidationIssue]:
        """
        Check for overlapping transcript entries of the same type.
        
        Note: Event and utterance types can overlap (they represent different aspects
        of the same time period), but entries of the same type should not overlap.
        
        Args:
            entries: List of parsed transcript entries
            
        Returns:
            List of ValidationIssue objects for overlaps found
        """
        issues = []
        
        # Group entries by type
        event_entries = [entry for entry in entries if entry['entry'].type == 'event']
        utterance_entries = [entry for entry in entries if entry['entry'].type == 'utterance']
        
        # Check overlaps within event entries
        event_issues = self._check_overlaps_within_type(event_entries, 'event')
        issues.extend(event_issues)
        
        # Check overlaps within utterance entries
        utterance_issues = self._check_overlaps_within_type(utterance_entries, 'utterance')
        issues.extend(utterance_issues)
        
        return issues
    
    def _check_overlaps_within_type(self, entries: List[Dict], entry_type: str) -> List[ValidationIssue]:
        """
        Check for overlaps within entries of the same type.
        
        Args:
            entries: List of parsed transcript entries of the same type
            entry_type: Type of entries being checked ('event' or 'utterance')
            
        Returns:
            List of ValidationIssue objects for overlaps found
        """
        issues = []
        
        if len(entries) < 2:
            return issues
        
        # Sort entries by start time
        sorted_entries = sorted(entries, key=lambda x: x['start_seconds'])
        
        for i in range(1, len(sorted_entries)):
            prev_entry = sorted_entries[i-1]
            curr_entry = sorted_entries[i]
            
            # Check for overlap
            if curr_entry['start_seconds'] < prev_entry['end_seconds']:
                overlap_duration = prev_entry['end_seconds'] - curr_entry['start_seconds']
                
                issues.append(ValidationIssue(
                    issue_type='overlap',
                    severity='warning',
                    start_time=curr_entry['start_seconds'],
                    end_time=prev_entry['end_seconds'],
                    description=f"Overlap between {entry_type} entries: {overlap_duration:.2f} seconds "
                              f"(from {curr_entry['entry'].start_time} to {prev_entry['entry'].end_time})",
                    entry_index=curr_entry['index'],
                    entry_data={
                        'overlap_duration': overlap_duration,
                        'current_entry': curr_entry['entry'].to_dict(),
                        'overlapping_entry': prev_entry['entry'].to_dict()
                    }
                ))
        
        return issues
    
    def _check_failed_chunks(self, entries: List[Dict]) -> List[ValidationIssue]:
        """
        Check for failed chunks (empty or very short entries).
        
        Args:
            entries: List of parsed transcript entries
            
        Returns:
            List of ValidationIssue objects for failed chunks
        """
        issues = []
        
        for entry_data in entries:
            entry = entry_data['entry']
            
            # Check for empty text
            if not entry.text or entry.text.strip() == '':
                issues.append(ValidationIssue(
                    issue_type='failed_chunk',
                    severity='error',
                    start_time=entry_data['start_seconds'],
                    end_time=entry_data['end_seconds'],
                    description=f"Empty transcript entry at {entry.start_time}",
                    entry_index=entry_data['index'],
                    entry_data={
                        'entry': entry.to_dict(),
                        'issue': 'empty_text'
                    }
                ))
            
            # Check for very short entries (less than 1 second and no meaningful content)
            elif entry_data['duration'] < 1.0 and len(entry.text.strip()) < 10:
                issues.append(ValidationIssue(
                    issue_type='failed_chunk',
                    severity='warning',
                    start_time=entry_data['start_seconds'],
                    end_time=entry_data['end_seconds'],
                    description=f"Very short entry with minimal content: '{entry.text.strip()}'",
                    entry_index=entry_data['index'],
                    entry_data={
                        'entry': entry.to_dict(),
                        'issue': 'short_content',
                        'duration': entry_data['duration'],
                        'text_length': len(entry.text.strip())
                    }
                ))
            
            # Check for entries with only punctuation or filler words
            elif self._is_filler_content(entry.text):
                issues.append(ValidationIssue(
                    issue_type='failed_chunk',
                    severity='info',
                    start_time=entry_data['start_seconds'],
                    end_time=entry_data['end_seconds'],
                    description=f"Entry contains only filler content: '{entry.text.strip()}'",
                    entry_index=entry_data['index'],
                    entry_data={
                        'entry': entry.to_dict(),
                        'issue': 'filler_content',
                        'text': entry.text.strip()
                    }
                ))
        
        return issues
    
    def _is_filler_content(self, text: str) -> bool:
        """
        Check if text contains only filler content.
        
        Args:
            text: Text to check
            
        Returns:
            True if text is only filler content
        """
        if not text or not text.strip():
            return True
        
        text_lower = text.lower().strip()
        
        # Common filler patterns
        filler_patterns = [
            r'^[.,!?;:\s]+$',  # Only punctuation and whitespace
            r'^(um|uh|er|ah|oh)\s*$',  # Common filler words
            r'^[a-z]\s*$',  # Single letter
            r'^[0-9]+\s*$',  # Only numbers
        ]
        
        for pattern in filler_patterns:
            if re.match(pattern, text_lower):
                return True
        
        return False
    
    def generate_validation_report(self, results: ValidationResults, output_path: Optional[Union[str, Path]] = None) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            results: ValidationResults object
            output_path: Optional path to save the report
            
        Returns:
            Report as string
        """
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("TRANSCRIPT VALIDATION REPORT")
        report_lines.append("=" * 60)
        report_lines.append(f"Video ID: {results.video_id}")
        report_lines.append(f"Validation Date: {results.validation_date}")
        report_lines.append(f"Total Entries: {results.total_entries}")
        report_lines.append(f"Total Duration: {results.total_duration_seconds:.2f} seconds")
        report_lines.append(f"Gap Threshold: {results.gap_threshold_seconds} seconds")
        report_lines.append("")
        
        # Summary
        summary = results.get_summary()
        report_lines.append("SUMMARY:")
        report_lines.append("-" * 20)
        report_lines.append(f"Validation Passed: {'✓' if summary['validation_passed'] else '✗'}")
        report_lines.append(f"Total Issues: {summary['total_issues']}")
        report_lines.append(f"  - Errors: {summary['errors']}")
        report_lines.append(f"  - Warnings: {summary['warnings']}")
        report_lines.append(f"  - Info: {summary['info']}")
        report_lines.append(f"Chronological Order Valid: {'✓' if summary['chronological_order_valid'] else '✗'}")
        report_lines.append(f"Gaps Found: {summary['gaps_found']}")
        report_lines.append(f"Failed Chunks: {summary['failed_chunks']}")
        report_lines.append(f"Overlaps Found: {summary['overlaps_found']}")
        report_lines.append("")
        
        # Detailed issues
        if results.issues:
            report_lines.append("DETAILED ISSUES:")
            report_lines.append("-" * 20)
            
            for i, issue in enumerate(results.issues, 1):
                report_lines.append(f"{i}. {issue.issue_type.upper()} ({issue.severity.upper()})")
                report_lines.append(f"   Time: {issue.start_time:.2f}s - {issue.end_time:.2f}s")
                report_lines.append(f"   Description: {issue.description}")
                if issue.entry_index is not None:
                    report_lines.append(f"   Entry Index: {issue.entry_index}")
                if issue.chunk_index is not None:
                    report_lines.append(f"   Chunk Index: {issue.chunk_index}")
                report_lines.append("")
        else:
            report_lines.append("No issues found! ✓")
        
        report_text = "\n".join(report_lines)
        
        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"Validation report saved to: {output_path}")
        
        return report_text
    
    def generate_detailed_json_report(self, results: ValidationResults, output_path: Optional[Union[str, Path]] = None) -> Dict:
        """
        Generate a detailed JSON report with full entry data for issues.
        
        Args:
            results: ValidationResults object
            output_path: Optional path to save the JSON report
            
        Returns:
            Detailed JSON report as dictionary
        """
        # Create detailed report structure
        detailed_report = {
            'validation_summary': {
                'video_id': results.video_id,
                'validation_date': results.validation_date,
                'total_entries': results.total_entries,
                'total_duration_seconds': results.total_duration_seconds,
                'gap_threshold_seconds': results.gap_threshold_seconds,
                'validation_passed': results.validation_passed,
                'chronological_order_valid': results.chronological_order_valid,
                'gaps_found': results.gaps_found,
                'failed_chunks': len(results.failed_chunks),
                'overlaps_found': results.overlaps_found
            },
            'issue_summary': results.get_summary(),
            'detailed_issues': []
        }
        
        # Group issues by type for better organization
        issues_by_type = {}
        for issue in results.issues:
            issue_type = issue.issue_type
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue.to_dict())
        
        # Add organized issues to report
        for issue_type, issues in issues_by_type.items():
            detailed_report['detailed_issues'].append({
                'issue_type': issue_type,
                'count': len(issues),
                'issues': issues
            })
        
        # Add statistics by severity
        severity_stats = {}
        for issue in results.issues:
            severity = issue.severity
            if severity not in severity_stats:
                severity_stats[severity] = 0
            severity_stats[severity] += 1
        
        detailed_report['severity_breakdown'] = severity_stats
        
        # Save to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(detailed_report, f, indent=2, ensure_ascii=False)
            print(f"Detailed JSON report saved to: {output_path}")
        
        return detailed_report
