#!/usr/bin/env python3
"""
Main transcription pipeline orchestrator.

This module provides the main TranscriptionPipeline class that coordinates
all the modular components for video transcription.
"""

import os
import json
import datetime
import time
from pathlib import Path
from typing import Dict, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import TranscriptionConfig, PipelineResults, FullTranscript, CacheEntry, CleanTranscript
from core.chunking import VideoChunker, ChunkProcessor
from core.transcription import TranscriptAnalyzer, TranscriptCombiner, TranscriptFormatter
from core.processing import ParallelProcessor, ResultProcessor
from core.validation import TranscriptValidator
from ai import GeminiClient, PromptManager, ModelHandler
from storage import CacheManager, FileStorage, UploadManager, VideoRepository
from utils import validate_video_file, get_video_duration
from core.file_manager import create_file_manager
from database import TranscriptionStorage


class TranscriptionPipeline:
    """
    Main transcription pipeline that orchestrates all components.
    
    This class coordinates the modular components to provide a clean,
    maintainable transcription pipeline.
    """
    
    def __init__(self, base_dir: str = "outputs", data_dir: str = "data", enable_file_management: bool = True, enable_video_repository: bool = True, enable_validation: bool = True, gap_threshold_seconds: float = 10.0, enable_mongodb: bool = False, mongodb_database: str = "multimodal_transcription"):
        """
        Initialize the transcription pipeline.
        
        Args:
            base_dir: Base directory for storing all outputs
            data_dir: Base directory for data management
            enable_file_management: Whether to enable automatic file management
            enable_video_repository: Whether to enable video repository (database-like interface)
            enable_validation: Whether to enable transcript validation
            gap_threshold_seconds: Gap threshold for validation (seconds)
            enable_mongodb: Whether to enable MongoDB storage for transcription results
            mongodb_database: MongoDB database name (default: multimodal_transcription)
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Create pipeline_runs directory to organize all runs
        self.pipeline_runs_dir = self.base_dir / "pipeline_runs"
        self.pipeline_runs_dir.mkdir(exist_ok=True)
        
        # Create timestamped run directory within pipeline_runs
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"transcription_run_{timestamp}"
        self.run_dir = self.pipeline_runs_dir / self.run_id
        self.run_dir.mkdir(exist_ok=True)
        
        # Create structured directories within the run
        (self.run_dir / "videos").mkdir(exist_ok=True)
        (self.run_dir / "chunks").mkdir(exist_ok=True)
        (self.run_dir / "transcripts").mkdir(exist_ok=True)
        (self.run_dir / "cache").mkdir(exist_ok=True)
        (self.run_dir / "logs").mkdir(exist_ok=True)
        
        # Initialize components
        self._initialize_components()
        
        # Initialize video repository if enabled
        self.video_repository = None
        if enable_video_repository:
            self.video_repository = VideoRepository(data_dir)
            print(f"Video repository enabled: {data_dir}")
        
        # Initialize file manager if enabled
        self.file_manager = None
        if enable_file_management:
            self.file_manager = create_file_manager(data_dir, auto_organize=True)
            print(f"File management enabled: {data_dir}")
        
        # Initialize transcript validator if enabled
        self.transcript_validator = None
        self.gap_threshold_seconds = gap_threshold_seconds
        if enable_validation:
            self.transcript_validator = TranscriptValidator(gap_threshold_seconds=gap_threshold_seconds)
            print(f"Transcript validation enabled with gap threshold: {gap_threshold_seconds}s")
        
        # Initialize MongoDB storage if enabled
        self.transcription_storage = None
        self.enable_mongodb = enable_mongodb
        if enable_mongodb:
            try:
                self.transcription_storage = TranscriptionStorage(database_name=mongodb_database)
                if self.transcription_storage.connect():
                    print(f"MongoDB storage enabled: {mongodb_database}")
                else:
                    print("⚠️ MongoDB connection failed, continuing without MongoDB storage")
                    self.transcription_storage = None
                    self.enable_mongodb = False
            except Exception as e:
                print(f"⚠️ MongoDB initialization failed: {e}")
                print("Continuing without MongoDB storage")
                self.transcription_storage = None
                self.enable_mongodb = False
        
        # Create run metadata
        self.run_metadata = {
            "run_id": self.run_id,
            "start_time": datetime.datetime.now().isoformat(),
            "base_dir": str(self.base_dir),
            "pipeline_runs_dir": str(self.pipeline_runs_dir),
            "run_dir": str(self.run_dir),
            "file_management_enabled": enable_file_management,
            "video_repository_enabled": enable_video_repository,
            "validation_enabled": enable_validation,
            "gap_threshold_seconds": gap_threshold_seconds,
            "runtime_tracking_enabled": True,
            "mongodb_enabled": self.enable_mongodb,
            "mongodb_database": mongodb_database if self.enable_mongodb else None
        }
        
        print(f"Transcription pipeline run initialized: {self.run_id}")
        print(f"Pipeline runs directory: {self.pipeline_runs_dir}")
        print(f"Run directory: {self.run_dir}")
    
    def _initialize_components(self):
        """Initialize all pipeline components."""
        # Initialize AI components
        self.model_handler = ModelHandler()
        self.gemini_client = GeminiClient(self.model_handler.current_model)
        self.prompt_manager = PromptManager()
        
        # Initialize storage components
        self.cache_manager = CacheManager(self.base_dir)
        self.file_storage = FileStorage(self.run_dir)
        self.upload_manager = UploadManager(self.run_dir / "cache")
        
        # Initialize core components
        self.video_chunker = VideoChunker(self.run_dir)
        self.chunk_processor = ChunkProcessor(self.run_dir)
        self.transcript_analyzer = TranscriptAnalyzer(
            self.gemini_client, self.prompt_manager, self.run_dir
        )
        self.transcript_combiner = TranscriptCombiner(self.run_dir)
        self.transcript_formatter = TranscriptFormatter(self.run_dir)
        self.parallel_processor = ParallelProcessor()
        self.result_processor = ResultProcessor(self.run_dir)
    
    def get_video_id(self, video_input: str) -> str:
        """Generate unique video ID from local video file path."""
        return Path(video_input).stem
    
    def resolve_video_input(self, video_input: str) -> tuple[str, Optional[str], bool]:
        """
        Resolve video input using repository or file system.
        
        Args:
            video_input: Video path, ID, or filename
            
        Returns:
            Tuple of (resolved_path, video_id, is_managed)
        """
        # Try repository lookup first if enabled
        if self.video_repository:
            # Try by video ID
            video_entity = self.video_repository.find_by_id(video_input)
            if video_entity:
                return video_entity.file_path, video_entity.video_id, True
            
            # Try by filename
            video_entity = self.video_repository.find_by_filename(video_input)
            if video_entity:
                return video_entity.file_path, video_entity.video_id, True
            
            # Try by file path
            video_entity = self.video_repository.find_by_path(video_input)
            if video_entity:
                return video_entity.file_path, video_entity.video_id, True
        
        # Fallback to file system
        video_path = Path(video_input)
        if video_path.exists():
            video_id = video_path.stem
            return str(video_path), video_id, False
        
        # If not found, return original input
        return video_input, Path(video_input).stem, False
    
    def process_video(self, config: TranscriptionConfig) -> PipelineResults:
        """
        Process a video through the transcription pipeline.
        
        Args:
            config: TranscriptionConfig object containing all pipeline settings
            
        Returns:
            PipelineResults: Pipeline results with transcript and metadata
        """
        # Start timing
        start_time = datetime.datetime.now()
        start_timestamp = start_time.isoformat()
        start_time_seconds = time.time()
        
        print(f"Starting transcription pipeline for: {config.video_input}")
        print(f"Run ID: {self.run_id}")
        print(f"Start time: {start_timestamp}")
        print(f"Configuration: {config}")
        
        # Resolve video input using repository or file system
        resolved_path, video_id, is_managed = self.resolve_video_input(config.video_input)
        print(f"\n=== Video Resolution ===")
        print(f"Resolved path: {resolved_path}")
        print(f"Video ID: {video_id}")
        print(f"Repository managed: {is_managed}")
        
        # Update config with resolved information
        config.video_input = resolved_path
        config.video_id = video_id
        config.file_managed = is_managed
        config.original_input = config.video_input if is_managed else None
        
        # Validate video file
        is_valid, error_msg = validate_video_file(resolved_path)
        if not is_valid:
            raise ValueError(f"Invalid video file: {error_msg}")
        
        # Handle file management if enabled and not already managed
        if self.file_manager and not is_managed:
            print(f"\n=== File Management ===")
            # Resolve video path through file manager
            resolved_path, is_new = self.file_manager.resolve_video_path(config.video_input)
            print(f"Resolved video path: {resolved_path}")
            print(f"New file: {is_new}")
            
            # Update config with resolved path
            config.video_input = resolved_path
            config.file_managed = not is_new
        
        # Store current configuration
        self._current_config = config.to_dict()
        config_hash = config.get_config_hash()
        
        print(f"Final Video ID: {video_id}")
        
        # Check for existing transcript with same configuration
        if not config.force_reprocess:
            existing_transcript = self.cache_manager.check_existing_transcript(video_id, config)
            if existing_transcript:
                print(f"\n=== Using Existing Transcript ===")
                print(f"Found cached transcript with matching configuration")
                
                # Load the existing transcript
                transcript_path = Path(existing_transcript['transcript_path'])
                with open(transcript_path, 'r') as f:
                    full_transcript_data = json.load(f)
                
                # Create results structure
                cached_chunk_duration = full_transcript_data.get('metadata', {}).get('pipeline_configuration', {}).get('chunk_duration', config.chunk_duration)
                
                # End timing for cached results
                end_time = datetime.datetime.now()
                end_timestamp = end_time.isoformat()
                total_runtime_seconds = time.time() - start_time_seconds
                
                pipeline_results = PipelineResults(
                    video_id=video_id,
                    original_input=config.video_input,
                    processing_date=datetime.datetime.now().isoformat(),
                    chunk_duration=cached_chunk_duration,
                    max_workers=config.max_workers,
                    transcript_analysis={},  # Empty for cached results
                    full_transcript=FullTranscript.from_dict(full_transcript_data),
                    cached=True,
                    cache_info=CacheEntry.from_dict(existing_transcript),
                    start_time=start_timestamp,
                    end_time=end_timestamp,
                    total_runtime_seconds=total_runtime_seconds,
                    processing_runtime_seconds=0.0,  # No processing for cached results
                    video_entity_id=video_id,
                    repository_managed=is_managed,
                    file_hash=config.get_config_hash() if is_managed else None
                )
                
                print(f"Using cached transcript: {transcript_path}")
                return pipeline_results
        
        print(f"\n=== Processing New Transcript ===")
        
        # Start processing timing
        processing_start_time = time.time()
        
        # Step 2: Copy video to pipeline directory
        video_path = self.file_storage.copy_video(config.video_input, video_id)
        
        # Step 3: Create chunks
        chunks_metadata = self.video_chunker.create_chunks(video_path, video_id, config)
        
        # Step 4: Generate transcripts for chunks using parallel processing
        print("\n=== Starting Parallel Transcript Generation ===")
        transcript_analysis = self.transcript_analyzer.analyze_all_chunks_parallel(
            chunks_metadata, video_id, config.max_workers
        )
        
        # Step 5: Create full transcript
        full_transcript = self.transcript_combiner.create_full_transcript(
            transcript_analysis, video_id, self._current_config
        )
        
        # Step 6: Create formatted outputs
        self.transcript_formatter.create_full_transcript_text(full_transcript, video_id)
        clean_transcript_dict = self.transcript_formatter.create_clean_transcript(full_transcript, video_id)
        
        # Step 6.5: Validate transcript if enabled
        validation_results = None
        if self.transcript_validator:
            print("\n=== Transcript Validation ===")
            # Convert dictionary to CleanTranscript object for validation
            clean_transcript_obj = CleanTranscript.from_dict(clean_transcript_dict)
            validation_results = self.transcript_validator.validate_transcript_object(clean_transcript_obj)
            
            # Also validate pipeline results for failed chunks
            pipeline_results_dict = {
                'video_id': video_id,
                'transcript_analysis': transcript_analysis,
                'full_transcript': clean_transcript_dict
            }
            pipeline_validation_results = self.transcript_validator.validate_pipeline_results(pipeline_results_dict, self.gap_threshold_seconds)
            
            # Merge failed chunk issues from pipeline validation
            if pipeline_validation_results.failed_chunks:
                print(f"  - Failed video chunks detected: {len(pipeline_validation_results.failed_chunks)}")
                validation_results.issues.extend([issue for issue in pipeline_validation_results.issues if issue.issue_type == 'failed_chunk'])
                validation_results.failed_chunks = pipeline_validation_results.failed_chunks
                validation_results.validation_passed = validation_results.validation_passed and len(pipeline_validation_results.failed_chunks) == 0
            
            # Generate validation report
            validation_report_path = self.run_dir / 'logs' / f'{video_id}_validation_report.txt'
            self.transcript_validator.generate_validation_report(validation_results, validation_report_path)
            
            # Generate detailed JSON report
            detailed_json_path = self.run_dir / 'logs' / f'{video_id}_validation_detailed.json'
            self.transcript_validator.generate_detailed_json_report(validation_results, detailed_json_path)
            
            # Print validation summary
            summary = validation_results.get_summary()
            print(f"Validation Results:")
            print(f"  - Passed: {'✓' if summary['validation_passed'] else '✗'}")
            print(f"  - Total Issues: {summary['total_issues']}")
            print(f"  - Errors: {summary['errors']}, Warnings: {summary['warnings']}, Info: {summary['info']}")
            print(f"  - Gaps: {summary['gaps_found']}, Failed Chunks: {summary['failed_chunks']}, Overlaps: {summary['overlaps_found']}")
            print(f"  - Chronological Order: {'✓' if summary['chronological_order_valid'] else '✗'}")
            
            # Show failed chunk details if any
            if validation_results.failed_chunks:
                print(f"  - Failed Video Chunks: {validation_results.failed_chunks}")
                for issue in validation_results.issues:
                    if issue.issue_type == 'failed_chunk' and issue.chunk_index is not None:
                        print(f"    - Chunk {issue.chunk_index}: {issue.description}")
            
            if not summary['validation_passed']:
                print(f"  ⚠️  Validation failed! Check reports:")
                print(f"    - Text report: {validation_report_path}")
                print(f"    - Detailed JSON: {detailed_json_path}")
            else:
                print(f"  ✓ Validation passed! Reports saved:")
                print(f"    - Text report: {validation_report_path}")
                print(f"    - Detailed JSON: {detailed_json_path}")
        
        # End processing timing
        processing_end_time = time.time()
        processing_runtime_seconds = processing_end_time - processing_start_time
        
        # Step 7: Create final results
        effective_chunk_duration = chunks_metadata.get('chunk_duration', config.chunk_duration)
        
        pipeline_results = PipelineResults(
            video_id=video_id,
            original_input=config.video_input,
            processing_date=datetime.datetime.now().isoformat(),
            chunk_duration=effective_chunk_duration,
            max_workers=config.max_workers,
            transcript_analysis=transcript_analysis,
            full_transcript=FullTranscript.from_dict(full_transcript),
            cached=False,
            start_time=start_timestamp,
            end_time=None,  # Will be set after cleanup
            total_runtime_seconds=None,  # Will be set after cleanup
            processing_runtime_seconds=processing_runtime_seconds,
            video_entity_id=video_id,
            repository_managed=is_managed,
            file_hash=config.get_config_hash() if is_managed else None
        )
        
        # Step 8: Save pipeline results
        output_path = self.result_processor.save_pipeline_results(pipeline_results, video_id)
        
        # Step 8.5: Save to MongoDB if enabled
        mongodb_doc_id = None
        if self.transcription_storage:
            try:
                print("\n=== Saving to MongoDB ===")
                mongodb_doc_id = self.transcription_storage.save_transcription_result(pipeline_results.to_dict())
                print(f"Saved to MongoDB with ID: {mongodb_doc_id}")
            except Exception as e:
                print(f"⚠️ Failed to save to MongoDB: {e}")
                print("Continuing without MongoDB save")
        
        # Step 9: Save transcript to global cache
        full_transcript_path = self.run_dir / 'transcripts' / f'{video_id}_full_transcript.json'
        self.cache_manager.save_transcript_cache(video_id, config_hash, str(full_transcript_path), config.to_dict())
        
        # Clean up uploaded files from Google if requested
        if config.cleanup_uploaded_files:
            self.gemini_client.cleanup_uploaded_files()
        
        # Update video repository if enabled
        if self.video_repository:
            # Try to find existing video entity
            video_entity = self.video_repository.find_by_id(video_id)
            if not video_entity:
                # Create new video entity if not found
                video_entity = self.video_repository.create_from_file(resolved_path, video_id)
            
            # Update video entity with processing results
            video_entity.update_status(
                "transcribed",
                transcript_path=str(full_transcript_path),
                processing_date=pipeline_results.processing_date,
                run_id=self.run_id
            )
            self.video_repository.save(video_entity)
            print(f"Updated video repository for: {video_id}")
        
        # Update file management if enabled
        if self.file_manager:
            self.file_manager.update_video_status(
                config.video_input, 
                "transcribed",
                transcript_path=str(full_transcript_path),
                processing_date=pipeline_results.processing_date,
                run_id=self.run_id
            )
            print(f"Updated file management status for: {video_id}")
        
        # Final timing
        end_time = datetime.datetime.now()
        end_timestamp = end_time.isoformat()
        total_runtime_seconds = time.time() - start_time_seconds
        
        # Update pipeline results with final timing
        pipeline_results.end_time = end_timestamp
        pipeline_results.total_runtime_seconds = total_runtime_seconds
        
        print(f"\nTranscription pipeline completed successfully!")
        print(f"Run ID: {self.run_id}")
        print(f"Start time: {start_timestamp}")
        print(f"End time: {end_timestamp}")
        print(f"Total runtime: {total_runtime_seconds:.2f} seconds")
        print(f"Processing runtime: {processing_runtime_seconds:.2f} seconds")
        print(f"Results saved to: {output_path}")
        print(f"Structured outputs:")
        print(f"  - Video: {self.run_dir / 'videos' / f'{video_id}.mp4'}")
        print(f"  - Chunks: {self.run_dir / 'chunks' / video_id}")
        print(f"  - Transcripts: {self.run_dir / 'transcripts' / f'{video_id}_transcript.json'}")
        print(f"  - Full Transcript (JSON): {self.run_dir / 'transcripts' / f'{video_id}_full_transcript.json'}")
        print(f"  - Full Transcript (Text): {self.run_dir / 'transcripts' / f'{video_id}_full_transcript.txt'}")
        print(f"  - Clean Transcript: {self.run_dir / 'transcripts' / f'{video_id}_clean_transcript.json'}")
        if mongodb_doc_id:
            print(f"  - MongoDB Document ID: {mongodb_doc_id}")
        
        return pipeline_results
    
    def get_pipeline_info(self) -> Dict:
        """Get information about the current pipeline run."""
        return {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "base_dir": str(self.base_dir),
            "components": {
                "model_handler": self.model_handler.get_model_info(),
                "cache_manager": self.cache_manager.get_cache_stats(),
                "file_storage": self.file_storage.get_storage_stats(),
                "upload_manager": self.upload_manager.get_upload_stats()
            }
        }
    
    def validate_existing_transcript(self, transcript_path: str, gap_threshold_seconds: float = 10.0) -> Dict:
        """
        Validate an existing transcript file.
        
        Args:
            transcript_path: Path to the transcript file to validate
            gap_threshold_seconds: Gap threshold for validation
            
        Returns:
            Dictionary with validation results
        """
        if not self.transcript_validator:
            # Create a temporary validator
            validator = TranscriptValidator(gap_threshold_seconds=gap_threshold_seconds)
        else:
            validator = self.transcript_validator
        
        # Validate the transcript
        validation_results = validator.validate_clean_transcript(transcript_path)
        
        # Generate report
        report_path = Path(transcript_path).parent / f"{Path(transcript_path).stem}_validation_report.txt"
        validator.generate_validation_report(validation_results, report_path)
        
        return {
            'validation_results': validation_results,
            'report_path': str(report_path),
            'summary': validation_results.get_summary()
        }
    
    def cleanup(self):
        """Clean up pipeline resources."""
        # Clean up uploaded files
        self.gemini_client.cleanup_uploaded_files()
        
        # Clean up upload cache
        self.upload_manager.cleanup_upload_cache()
        
        # Disconnect from MongoDB if connected
        if self.transcription_storage:
            self.transcription_storage.disconnect()
        
        print("Pipeline cleanup completed")
