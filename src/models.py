#!/usr/bin/env python3
"""
Data models and configuration classes for the transcription pipeline.

This module contains all the data structures, configuration classes,
and type definitions used throughout the transcription pipeline.
"""

import hashlib
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime


class ModelType(Enum):
    """Supported AI models for transcription."""
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_1_5_PRO = "gemini-1.5-pro"


class TranscriptType(Enum):
    """Types of transcript outputs."""
    FULL = "full"
    CLEAN = "clean"
    TEXT = "text"


@dataclass
class TranscriptionConfig:
    """
    Configuration class for transcription pipeline settings.
    
    This class provides validation and serialization for pipeline configuration,
    ensuring consistent behavior across different runs.
    """
    # Video processing settings
    video_input: str
    chunk_duration: int = 300
    chunk_size_mb: Optional[int] = None  # Size-based chunking in MB
    max_workers: int = 4
    
    # Pipeline behavior settings
    cleanup_uploaded_files: bool = True
    force_reprocess: bool = False
    
    # AI model settings
    model: ModelType = ModelType.GEMINI_2_5_PRO
    
    # Output settings
    output_dir: str = "outputs"
    
    # Pipeline version for compatibility
    pipeline_version: str = "1.0"
    
    # Database-compatible fields
    video_id: Optional[str] = None  # Video ID for database lookups
    file_managed: bool = False  # Whether file is managed by repository
    original_input: Optional[str] = None  # Original input before resolution
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration parameters."""
        if not self.video_input:
            raise ValueError("video_input cannot be empty")
        
        if self.chunk_duration <= 0:
            raise ValueError("chunk_duration must be positive")
        
        if self.chunk_duration > 3600:  # 1 hour
            raise ValueError("chunk_duration should not exceed 3600 seconds (1 hour)")
        
        if self.chunk_size_mb is not None:
            if self.chunk_size_mb <= 0:
                raise ValueError("chunk_size_mb must be positive")
            if self.chunk_size_mb > 1000:  # 1GB
                raise ValueError("chunk_size_mb should not exceed 1000 MB (1GB)")
        
        if self.max_workers <= 0:
            raise ValueError("max_workers must be positive")
        
        if self.max_workers > 16:
            raise ValueError("max_workers should not exceed 16 for performance reasons")
        
        if not isinstance(self.model, ModelType):
            if isinstance(self.model, str):
                try:
                    self.model = ModelType(self.model)
                except ValueError:
                    raise ValueError(f"Invalid model: {self.model}. Must be one of {[m.value for m in ModelType]}")
            else:
                raise ValueError(f"model must be a ModelType enum or string")
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary for serialization."""
        config_dict = asdict(self)
        # Convert enum to string for JSON serialization
        config_dict['model'] = self.model.value
        return config_dict
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'TranscriptionConfig':
        """Create configuration from dictionary."""
        # Convert string back to enum
        if 'model' in config_dict and isinstance(config_dict['model'], str):
            config_dict['model'] = ModelType(config_dict['model'])
        return cls(**config_dict)
    
    def get_config_hash(self) -> str:
        """Generate a hash for this configuration."""
        # Create a stable string representation for hashing
        chunk_size_str = f"_{self.chunk_size_mb}" if self.chunk_size_mb is not None else ""
        config_string = f"{self.video_input}_{self.chunk_duration}{chunk_size_str}_{self.max_workers}_{self.model.value}_{self.pipeline_version}"
        return hashlib.sha256(config_string.encode()).hexdigest()[:16]
    
    def is_compatible_with(self, other: 'TranscriptionConfig') -> bool:
        """Check if this configuration is compatible with another."""
        return (
            self.video_input == other.video_input and
            self.chunk_duration == other.chunk_duration and
            self.chunk_size_mb == other.chunk_size_mb and
            self.max_workers == other.max_workers and
            self.model == other.model and
            self.pipeline_version == other.pipeline_version
        )
    
    def get_display_name(self) -> str:
        """Get a human-readable name for this configuration."""
        video_name = Path(self.video_input).stem
        chunk_info = f"{self.chunk_size_mb}mb" if self.chunk_size_mb is not None else f"{self.chunk_duration}s"
        return f"{video_name}_{chunk_info}_{self.max_workers}w_{self.model.value}"
    
    @classmethod
    def from_video_entity(cls, video_entity, **kwargs) -> 'TranscriptionConfig':
        """
        Create TranscriptionConfig from VideoEntity.
        
        Args:
            video_entity: VideoEntity object
            **kwargs: Additional configuration parameters
            
        Returns:
            TranscriptionConfig instance
        """
        return cls(
            video_input=video_entity.file_path,
            video_id=video_entity.video_id,
            file_managed=True,
            original_input=video_entity.filename,
            **kwargs
        )
    
    def __str__(self) -> str:
        """String representation of configuration."""
        chunk_info = f"chunk_size_mb={self.chunk_size_mb}" if self.chunk_size_mb is not None else f"chunk_duration={self.chunk_duration}"
        return f"TranscriptionConfig(video_input='{self.video_input}', {chunk_info}, max_workers={self.max_workers}, model={self.model.value})"


@dataclass
class TranscriptEntry:
    """Individual transcript entry with timing and content."""
    time: str  # Main time field for backward compatibility
    speaker: str
    spoken_text: str
    visual_description: str
    absolute_time: float  # Used for sorting
    absolute_start_timestamp: str  # Used in text output
    absolute_end_timestamp: str  # Used in text output
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TranscriptEntry':
        """Create TranscriptEntry from dictionary."""
        return cls(
            time=data.get('time', ''),
            speaker=data.get('speaker', ''),
            spoken_text=data.get('spoken_text', ''),
            visual_description=data.get('visual_description', ''),
            absolute_time=data.get('absolute_time', 0.0),
            absolute_start_timestamp=data.get('absolute_start_timestamp', ''),
            absolute_end_timestamp=data.get('absolute_end_timestamp', '')
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TranscriptMetadata:
    """Metadata for transcript files."""
    total_entries: int
    total_duration_seconds: float
    generation_date: str
    pipeline_configuration: Dict[str, Any]
    run_id: str
    video_id: str
    transcript_type: TranscriptType = TranscriptType.FULL
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TranscriptMetadata':
        """Create TranscriptMetadata from dictionary."""
        return cls(
            total_entries=data.get('total_entries', 0),
            total_duration_seconds=data.get('total_duration_seconds', 0.0),
            generation_date=data.get('generation_date', ''),
            pipeline_configuration=data.get('pipeline_configuration', {}),
            run_id=data.get('run_id', ''),
            video_id=data.get('video_id', ''),
            transcript_type=TranscriptType(data.get('transcript_type', 'full'))
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = asdict(self)
        result['transcript_type'] = self.transcript_type.value
        return result


@dataclass
class FullTranscript:
    """Complete transcript structure with metadata and entries."""
    video_id: str
    transcript_type: TranscriptType
    metadata: TranscriptMetadata
    transcript: List[TranscriptEntry]
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FullTranscript':
        """Create FullTranscript from dictionary."""
        return cls(
            video_id=data.get('video_id', ''),
            transcript_type=TranscriptType(data.get('transcript_type', 'full')),
            metadata=TranscriptMetadata.from_dict(data.get('metadata', {})),
            transcript=[TranscriptEntry.from_dict(entry) for entry in data.get('transcript', [])]
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'video_id': self.video_id,
            'transcript_type': self.transcript_type.value,
            'metadata': self.metadata.to_dict(),
            'transcript': [entry.to_dict() for entry in self.transcript]
        }


@dataclass
class CleanTranscriptEntry:
    """Clean transcript entry with minimal fields."""
    type: str = "utterance"
    start_time: str = ""
    end_time: str = ""
    speaker: str = ""
    text: str = ""
    visual: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CleanTranscriptEntry':
        """Create CleanTranscriptEntry from dictionary."""
        return cls(
            type=data.get('type', 'utterance'),
            start_time=data.get('start_time', ''),
            end_time=data.get('end_time', ''),
            speaker=data.get('speaker', ''),
            text=data.get('text', ''),
            visual=data.get('visual')
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = asdict(self)
        # Remove None values
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class CleanTranscript:
    """Clean transcript structure with minimal metadata."""
    video_id: str
    duration_seconds: float
    total_entries: int
    generated: str
    pipeline_configuration: Dict[str, Any]
    run_id: str
    transcript: List[CleanTranscriptEntry]
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CleanTranscript':
        """Create CleanTranscript from dictionary."""
        return cls(
            video_id=data.get('video_id', ''),
            duration_seconds=data.get('duration_seconds', 0.0),
            total_entries=data.get('total_entries', 0),
            generated=data.get('generated', ''),
            pipeline_configuration=data.get('pipeline_configuration', {}),
            run_id=data.get('run_id', ''),
            transcript=[CleanTranscriptEntry.from_dict(entry) for entry in data.get('transcript', [])]
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'video_id': self.video_id,
            'duration_seconds': self.duration_seconds,
            'total_entries': self.total_entries,
            'generated': self.generated,
            'pipeline_configuration': self.pipeline_configuration,
            'run_id': self.run_id,
            'transcript': [entry.to_dict() for entry in self.transcript]
        }


@dataclass
class CacheEntry:
    """Cache entry for stored transcripts."""
    video_id: str
    config_hash: str
    transcript_path: str
    generation_date: str
    configuration: Dict[str, Any]
    cache_file: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CacheEntry':
        """Create CacheEntry from dictionary."""
        return cls(
            video_id=data.get('video_id', ''),
            config_hash=data.get('config_hash', ''),
            transcript_path=data.get('transcript_path', ''),
            generation_date=data.get('generation_date', ''),
            configuration=data.get('configuration', {}),
            cache_file=data.get('cache_file', '')
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PipelineResults:
    """Results from a pipeline run."""
    video_id: str
    original_input: str
    processing_date: str
    chunk_duration: int
    max_workers: int
    transcript_analysis: Dict[str, Any]
    full_transcript: FullTranscript
    cached: bool = False
    cache_info: Optional[CacheEntry] = None
    
    # Runtime tracking fields
    start_time: Optional[str] = None  # ISO format start time
    end_time: Optional[str] = None  # ISO format end time
    total_runtime_seconds: Optional[float] = None  # Total runtime in seconds
    processing_runtime_seconds: Optional[float] = None  # Processing time (excluding setup/cleanup)
    
    # Database-compatible fields
    video_entity_id: Optional[str] = None  # Reference to VideoEntity
    repository_managed: bool = False  # Whether managed by repository
    file_hash: Optional[str] = None  # File hash for deduplication
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PipelineResults':
        """Create PipelineResults from dictionary."""
        return cls(
            video_id=data.get('video_id', ''),
            original_input=data.get('original_input', ''),
            processing_date=data.get('processing_date', ''),
            chunk_duration=data.get('chunk_duration', 0),
            max_workers=data.get('max_workers', 0),
            transcript_analysis=data.get('transcript_analysis', {}),
            full_transcript=FullTranscript.from_dict(data.get('full_transcript', {})),
            cached=data.get('cached', False),
            cache_info=CacheEntry.from_dict(data.get('cache_info', {})) if data.get('cache_info') else None,
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            total_runtime_seconds=data.get('total_runtime_seconds'),
            processing_runtime_seconds=data.get('processing_runtime_seconds')
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = asdict(self)
        result['full_transcript'] = self.full_transcript.to_dict()
        if self.cache_info:
            result['cache_info'] = self.cache_info.to_dict()
        return result


@dataclass
class ChunkMetadata:
    """Metadata for video chunks."""
    chunk_path: str
    start_time: float
    end_time: float
    duration: float
    chunk_index: int
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChunkMetadata':
        """Create ChunkMetadata from dictionary."""
        return cls(
            chunk_path=data.get('chunk_path', ''),
            start_time=data.get('start_time', 0.0),
            end_time=data.get('end_time', 0.0),
            duration=data.get('duration', 0.0),
            chunk_index=data.get('chunk_index', 0)
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class UploadedFileInfo:
    """Information about uploaded files."""
    file_id: str
    state: str
    file_hash: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UploadedFileInfo':
        """Create UploadedFileInfo from dictionary."""
        return cls(
            file_id=data.get('file_id', ''),
            state=data.get('state', ''),
            file_hash=data.get('file_hash', '')
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ValidationIssue:
    """Individual validation issue found in transcript."""
    issue_type: str  # 'chronological_order', 'gap', 'failed_chunk', 'overlap'
    severity: str  # 'error', 'warning', 'info'
    start_time: float
    end_time: float
    description: str
    entry_index: Optional[int] = None
    chunk_index: Optional[int] = None
    entry_data: Optional[Dict] = None  # Full entry data for detailed analysis
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = asdict(self)
        # Remove None values for cleaner output
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class ValidationResults:
    """Results from transcript validation."""
    video_id: str
    validation_date: str
    total_entries: int
    total_duration_seconds: float
    issues: List[ValidationIssue]
    chronological_order_valid: bool
    gap_threshold_seconds: float
    gaps_found: int
    failed_chunks: List[int]
    overlaps_found: int
    validation_passed: bool
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ValidationResults':
        """Create ValidationResults from dictionary."""
        return cls(
            video_id=data.get('video_id', ''),
            validation_date=data.get('validation_date', ''),
            total_entries=data.get('total_entries', 0),
            total_duration_seconds=data.get('total_duration_seconds', 0.0),
            issues=[ValidationIssue(**issue) for issue in data.get('issues', [])],
            chronological_order_valid=data.get('chronological_order_valid', True),
            gap_threshold_seconds=data.get('gap_threshold_seconds', 10.0),
            gaps_found=data.get('gaps_found', 0),
            failed_chunks=data.get('failed_chunks', []),
            overlaps_found=data.get('overlaps_found', 0),
            validation_passed=data.get('validation_passed', True)
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'video_id': self.video_id,
            'validation_date': self.validation_date,
            'total_entries': self.total_entries,
            'total_duration_seconds': self.total_duration_seconds,
            'issues': [issue.to_dict() for issue in self.issues],
            'chronological_order_valid': self.chronological_order_valid,
            'gap_threshold_seconds': self.gap_threshold_seconds,
            'gaps_found': self.gaps_found,
            'failed_chunks': self.failed_chunks,
            'overlaps_found': self.overlaps_found,
            'validation_passed': self.validation_passed
        }
    
    def get_summary(self) -> Dict:
        """Get a summary of validation results."""
        error_count = sum(1 for issue in self.issues if issue.severity == 'error')
        warning_count = sum(1 for issue in self.issues if issue.severity == 'warning')
        info_count = sum(1 for issue in self.issues if issue.severity == 'info')
        
        return {
            'validation_passed': self.validation_passed,
            'total_issues': len(self.issues),
            'errors': error_count,
            'warnings': warning_count,
            'info': info_count,
            'chronological_order_valid': self.chronological_order_valid,
            'gaps_found': self.gaps_found,
            'failed_chunks': len(self.failed_chunks),
            'overlaps_found': self.overlaps_found
        }
