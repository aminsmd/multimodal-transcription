#!/usr/bin/env python3
"""
Video chunking functionality for the transcription pipeline.

This module handles video segmentation into smaller chunks for processing.
"""

import os
import json
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import TranscriptionConfig
from utils import get_ffmpeg_primary_stream_map_args, get_primary_audio_stream, get_video_duration


class VideoChunker:
    """
    Handles video chunking operations for the transcription pipeline.
    """
    
    def __init__(self, run_dir: Path):
        """
        Initialize the video chunker.
        
        Args:
            run_dir: Directory for storing chunks and metadata
        """
        self.run_dir = run_dir
        self.chunks_dir = run_dir / "chunks"
        self.chunks_dir.mkdir(exist_ok=True)
    
    def create_chunks(self, video_path: str, video_id: str, config: TranscriptionConfig) -> Dict:
        """
        Create video chunks based on configuration.
        
        Args:
            video_path: Path to the video file
            video_id: Unique identifier for the video
            config: Transcription configuration
            
        Returns:
            Dictionary containing chunk metadata
        """
        chunks_dir = self.chunks_dir / video_id
        chunks_dir.mkdir(exist_ok=True)
        
        # Check if chunks already exist
        metadata_path = self.chunks_dir / f"{video_id}_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Check if all chunk files exist
            all_chunks_exist = True
            for chunk_info in metadata["chunks"]:
                chunk_path = chunks_dir / f"chunk_{chunk_info['start_time']}_{chunk_info['end_time']}.mp4"
                if not chunk_path.exists():
                    all_chunks_exist = False
                    break
            
            if all_chunks_exist:
                print(f"Chunks already exist for video {video_id}")
                return metadata
        
        print(f"Creating chunks from video: {video_path}")
        
        duration = get_video_duration(video_path)
        if duration <= 0:
            raise ValueError(f"Could not determine video duration: {video_path}")

        stream_map_args = get_ffmpeg_primary_stream_map_args(video_path)
        source_has_audio = get_primary_audio_stream(video_path) is not None

        chunks = []

        if config.chunk_size_mb is not None:
            # Size-based chunking
            print(f"Using size-based chunking with target size: {config.chunk_size_mb}MB")
            chunk_boundaries, calculated_chunk_duration = self._calculate_size_based_chunks(
                video_path, duration, config.chunk_size_mb, stream_map_args
            )
            effective_chunk_duration = int(calculated_chunk_duration)
        else:
            # Time-based chunking
            print(f"Using time-based chunking with duration: {config.chunk_duration}s")
            chunk_boundaries = []
            for i in range(0, int(duration), config.chunk_duration):
                start_time = i
                end_time = min(i + config.chunk_duration, duration)
                chunk_boundaries.append((start_time, end_time))
            effective_chunk_duration = config.chunk_duration

        total_chunks = len(chunk_boundaries)

        for chunk_index, (start_time, end_time) in enumerate(chunk_boundaries, 1):
            chunk_path = chunks_dir / f"chunk_{start_time}_{end_time}.mp4"

            self._create_chunk_file(
                video_path,
                chunk_path,
                start_time,
                end_time,
                stream_map_args,
                source_has_audio,
                chunk_index,
                total_chunks
            )

            chunks.append({
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "path": str(chunk_path)
            })
        
        # Create metadata
        metadata = {
            "video_id": video_id,
            "original_path": video_path,
            "total_duration": duration,
            "chunk_duration": effective_chunk_duration,
            "chunk_size_mb": config.chunk_size_mb,
            "chunking_method": "size_based" if config.chunk_size_mb is not None else "time_based",
            "num_chunks": len(chunks),
            "processing_date": datetime.datetime.now().isoformat(),
            "chunks": chunks
        }
        
        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Created {len(chunks)} chunks")
        return metadata

    def _create_chunk_file(
        self,
        video_path: str,
        chunk_path: Path,
        start_time: float,
        end_time: float,
        stream_map_args: List[str],
        source_has_audio: bool,
        chunk_index: int,
        total_chunks: int
    ) -> None:
        """
        Create a chunk while preserving audio whenever possible.

        The fast path copies compatible streams without re-encoding. If that
        fails, transcode to common MP4 codecs instead of silently dropping audio.
        """
        duration = end_time - start_time

        copy_cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-ss', str(start_time),
            '-t', str(duration),
            *stream_map_args,
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            str(chunk_path)
        ]
        copy_success, copy_error = self._run_ffmpeg_command(copy_cmd)
        if copy_success:
            self._verify_chunk_audio(chunk_path, source_has_audio, start_time, end_time)
            if self._should_log_chunk_success(chunk_index, total_chunks):
                print(
                    f"Created chunk {chunk_index}/{total_chunks} "
                    f"({start_time}-{end_time}s) with primary streams"
                )
            return

        print(f"ffmpeg stream copy failed for chunk {chunk_index}/{total_chunks} ({start_time}-{end_time}s): {copy_error}")
        print(f"Retrying chunk {chunk_index}/{total_chunks} with audio-preserving transcode")

        transcode_cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-ss', str(start_time),
            '-t', str(duration),
            *stream_map_args,
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-avoid_negative_ts', 'make_zero',
            str(chunk_path)
        ]
        transcode_success, transcode_error = self._run_ffmpeg_command(transcode_cmd)
        if transcode_success:
            self._verify_chunk_audio(chunk_path, source_has_audio, start_time, end_time)
            print(f"Successfully transcoded chunk {chunk_index}/{total_chunks} ({start_time}-{end_time}s) with audio")
            return

        print(f"ffmpeg transcode failed for chunk {chunk_index}/{total_chunks} ({start_time}-{end_time}s): {transcode_error}")
        print(f"Retrying chunk {chunk_index}/{total_chunks} with MoviePy and audio enabled")

        try:
            from moviepy import VideoFileClip

            with VideoFileClip(video_path) as video:
                chunk_video = video.subclipped(start_time, end_time)
                chunk_video.write_videofile(
                    str(chunk_path),
                    codec='libx264',
                    audio=True,
                    audio_codec='aac',
                    logger=None
                )
                chunk_video.close()
        except Exception as e:
            raise RuntimeError(
                f"Unable to create chunk {start_time}-{end_time}. "
                f"stream copy error: {copy_error}; "
                f"transcode error: {transcode_error}; "
                f"MoviePy error: {e}"
            )

        if not chunk_path.exists() or chunk_path.stat().st_size == 0:
            raise RuntimeError(f"MoviePy created an empty or missing chunk: {chunk_path}")

        self._verify_chunk_audio(chunk_path, source_has_audio, start_time, end_time)
        print(f"Successfully created chunk {chunk_index}/{total_chunks} ({start_time}-{end_time}s) with MoviePy audio")

    def _verify_chunk_audio(
        self,
        chunk_path: Path,
        source_has_audio: bool,
        start_time: float,
        end_time: float
    ) -> None:
        """Fail fast if a chunk lost audio that existed in the source video."""
        if not source_has_audio:
            return

        if get_primary_audio_stream(str(chunk_path)) is None:
            raise RuntimeError(
                f"Chunk {start_time}-{end_time} is missing audio, but source video has audio: {chunk_path}"
            )

    def _should_log_chunk_success(self, chunk_index: int, total_chunks: int) -> bool:
        """Log normal chunk progress without printing one line for every chunk."""
        return chunk_index == 1 or chunk_index == total_chunks or chunk_index % 10 == 0

    def _run_ffmpeg_command(self, cmd: List[str]) -> Tuple[bool, str]:
        """Run an ffmpeg command and return success plus a concise error."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            return False, str(e)

        if result.returncode == 0:
            return True, ""

        error = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        return False, error[-2000:]
    
    def _calculate_size_based_chunks(
        self,
        video_path: str,
        duration: float,
        target_size_mb: int,
        stream_map_args: List[str]
    ) -> Tuple[List[Tuple[float, float]], float]:
        """
        Calculate chunk boundaries based on target file size.
        
        Args:
            video_path: Path to the video file
            duration: Video duration in seconds
            target_size_mb: Target chunk size in MB
            stream_map_args: ffmpeg stream selection arguments
            
        Returns:
            Tuple of (chunk_boundaries, average_chunk_duration)
        """
        print(f"Calculating size-based chunk boundaries for target size: {target_size_mb}MB")
        
        # Get the original video file size
        original_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"Original video size: {original_size_mb:.1f}MB")
        
        # Estimate total number of chunks needed
        estimated_chunks = max(1, int(original_size_mb / target_size_mb))
        chunk_duration_estimate = duration / estimated_chunks
        
        print(f"Estimated {estimated_chunks} chunks with ~{chunk_duration_estimate:.1f}s duration each")
        
        # Sample a few chunks to get better size estimates
        sample_chunks = []
        sample_size = min(3, estimated_chunks)  # Sample up to 3 chunks
        
        for i in range(sample_size):
            start_time = i * chunk_duration_estimate
            end_time = min((i + 1) * chunk_duration_estimate, duration)
            
            # Create a temporary chunk to measure size
            temp_chunk_path = self.chunks_dir / f"temp_sample_{i}.mp4"
            try:
                cmd = [
                    'ffmpeg', '-y',
                    '-i', video_path,
                    '-ss', str(start_time),
                    '-t', str(end_time - start_time),
                    *stream_map_args,
                    '-c', 'copy',
                    '-avoid_negative_ts', 'make_zero',
                    str(temp_chunk_path)
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and temp_chunk_path.exists():
                    chunk_size_mb = os.path.getsize(temp_chunk_path) / (1024 * 1024)
                    sample_chunks.append((start_time, end_time, chunk_size_mb))
                    print(f"Sample chunk {i}: {start_time:.1f}s-{end_time:.1f}s = {chunk_size_mb:.1f}MB")
                # Clean up temp file
                if temp_chunk_path.exists():
                    temp_chunk_path.unlink()
            except Exception as e:
                print(f"Error creating sample chunk {i}: {e}")
        
        # Calculate average size per second from samples
        if sample_chunks:
            total_duration = sum(end - start_time for start_time, end, _ in sample_chunks)
            total_size = sum(size for _, _, size in sample_chunks)
            size_per_second = total_size / total_duration if total_duration > 0 else target_size_mb / 60
        else:
            # Fallback: assume uniform bitrate
            size_per_second = original_size_mb / duration
        
        print(f"Estimated size per second: {size_per_second:.2f}MB/s")
        
        # Calculate chunk boundaries
        chunk_boundaries = []
        current_time = 0.0
        
        while current_time < duration:
            # Calculate target duration for this chunk
            remaining_duration = duration - current_time
            target_duration = target_size_mb / size_per_second
            
            # Don't exceed remaining duration
            chunk_duration = min(target_duration, remaining_duration)
            end_time = current_time + chunk_duration
            
            chunk_boundaries.append((current_time, end_time))
            current_time = end_time
        
        print(f"Calculated {len(chunk_boundaries)} chunk boundaries")
        
        # Calculate average chunk duration from the actual boundaries
        if chunk_boundaries:
            total_duration = sum(end - start for start, end in chunk_boundaries)
            average_chunk_duration = total_duration / len(chunk_boundaries)
        else:
            average_chunk_duration = 0.0
        
        print(f"Average chunk duration: {average_chunk_duration:.1f}s")
        return chunk_boundaries, average_chunk_duration