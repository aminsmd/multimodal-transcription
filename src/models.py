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
        config_string = f"{self.video_input}_{self.chunk_duration}_{self.max_workers}_{self.model.value}_{self.pipeline_version}"
        return hashlib.sha256(config_string.encode()).hexdigest()[:16]
    
    def is_compatible_with(self, other: 'TranscriptionConfig') -> bool:
        """Check if this configuration is compatible with another."""
        return (
            self.video_input == other.video_input and
            self.chunk_duration == other.chunk_duration and
            self.max_workers == other.max_workers and
            self.model == other.model and
            self.pipeline_version == other.pipeline_version
        )
    
    def get_display_name(self) -> str:
        """Get a human-readable name for this configuration."""
        video_name = Path(self.video_input).stem
        return f"{video_name}_{self.chunk_duration}s_{self.max_workers}w_{self.model.value}"
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return f"TranscriptionConfig(video_input='{self.video_input}', chunk_duration={self.chunk_duration}, max_workers={self.max_workers}, model={self.model.value})"


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
            cache_info=CacheEntry.from_dict(data.get('cache_info', {})) if data.get('cache_info') else None
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
