# Multimodal Video Transcription Pipeline

A comprehensive video transcription system that uses Google's Gemini 2.5 Pro to generate detailed transcripts from video files. The pipeline processes videos in parallel, handles file management automatically, and outputs transcripts in multiple formats.

## 🎯 Features

- **Multimodal Analysis**: Uses Gemini 2.5 Pro for both audio and visual content analysis
- **Parallel Processing**: Processes video chunks simultaneously for faster transcription
- **Automatic File Management**: Organizes and tracks video files with deduplication
- **Multiple Output Formats**: JSON, text, and clean transcript formats
- **Smart Caching**: Avoids reprocessing identical videos with same configuration
- **Google API Integration**: Automatic file upload and cleanup
- **Robust Error Handling**: Graceful handling of processing errors and timeouts

## 📋 Requirements

- Python 3.8+
- Google API Key for Gemini
- FFmpeg (for video processing)
- Virtual environment (recommended)

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd multimodal-transcription

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Set your Google API key
export GOOGLE_API_KEY="your_api_key_here"

# Or create a .env file
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

### 3. Run Transcription

```bash
# Basic usage
python src/transcription_pipeline.py --input /path/to/video.mp4

# With custom settings
python src/transcription_pipeline.py \
  --input /path/to/video.mp4 \
  --chunk-size 300 \
  --max-workers 4 \
  --data-dir data \
  --output-dir outputs
```

## 📁 Project Structure

```
multimodal-transcription/
├── src/                          # Source code
│   ├── core/                     # Core components
│   │   └── file_manager.py      # File management system
│   ├── data/                     # Data management
│   │   ├── data_setup.py        # Data directory setup
│   │   └── setup_data.py        # Quick setup script
│   ├── utils/                    # Utility functions
│   │   ├── video_utils.py       # Video processing utilities
│   │   ├── file_utils.py         # File handling utilities
│   │   └── config_utils.py      # Configuration utilities
│   ├── models.py                 # Data models and configuration
│   └── transcription_pipeline.py # Main pipeline
├── examples/                     # Usage examples
│   ├── basic_usage.py           # Basic usage example
│   ├── advanced_usage.py        # Advanced features
│   ├── enhanced_usage.py        # File management example
│   └── data_management_example.py # Data management example
├── outputs/                      # Generated outputs
│   └── pipeline_runs/           # Timestamped run directories
├── data/                         # Data directory (auto-created)
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🔧 Command Line Usage

### Basic Commands

```bash
# Process a single video
python src/transcription_pipeline.py --input video.mp4

# Process with custom chunk size and workers
python src/transcription_pipeline.py \
  --input video.mp4 \
  --chunk-size 600 \
  --max-workers 8

# Disable file management
python src/transcription_pipeline.py \
  --input video.mp4 \
  --no-file-management

# Force reprocessing (ignore cache)
python src/transcription_pipeline.py \
  --input video.mp4 \
  --force-reprocess
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Video file path (required) | - |
| `--chunk-size` | Duration of each chunk in seconds | 300 |
| `--max-workers` | Number of parallel workers | 4 |
| `--output-dir` | Output directory | outputs |
| `--data-dir` | Data directory for file management | data |
| `--no-cleanup` | Skip cleanup of uploaded files | false |
| `--no-file-management` | Disable file management | false |
| `--force-reprocess` | Force reprocessing | false |

## 📊 Output Structure

### Directory Layout

```
outputs/
└── pipeline_runs/
    └── transcription_run_YYYYMMDD_HHMMSS/
        ├── videos/                    # Original video files
        ├── chunks/                    # Video chunks
        │   └── {video_id}/
        │       ├── chunk_0_300.mp4
        │       ├── chunk_300_600.mp4
        │       └── chunk_600_640.mp4
        ├── transcripts/               # Transcript files
        │   ├── {video_id}_transcript.json
        │   ├── {video_id}_full_transcript.json
        │   ├── {video_id}_full_transcript.txt
        │   └── {video_id}_clean_transcript.json
        ├── cache/                     # Processing cache
        └── logs/                      # Log files
```

### Output Files

#### 1. Full Transcript JSON (`{video_id}_full_transcript.json`)
Complete transcript with all metadata and timestamps.

```json
{
  "video_id": "example_video",
  "transcript_type": "full",
  "metadata": {
    "total_entries": 150,
    "total_duration_seconds": 1200.0,
    "generation_date": "2024-01-01T12:00:00",
    "pipeline_configuration": {
      "video_input": "/path/to/video.mp4",
      "chunk_duration": 300,
      "max_workers": 4,
      "model": "gemini-2.5-pro"
    }
  },
  "transcript": [
    {
      "time": "00:00:00.000",
      "speaker": "teacher",
      "spoken_text": "Good morning, class!",
      "visual_description": "Teacher stands at the front of the classroom",
      "absolute_time": 0.0,
      "absolute_start_timestamp": "00:00:00.000",
      "absolute_end_timestamp": "00:00:05.000"
    }
  ]
}
```

#### 2. Full Transcript Text (`{video_id}_full_transcript.txt`)
Human-readable text version.

```
================================================================================
FULL VIDEO TRANSCRIPT
================================================================================
Video ID: example_video
Generated: 2024-01-01T12:00:00
Total Entries: 150
Total Duration: 1200.0 seconds

[00:00 - 00:05] teacher: Good morning, class!

[00:05 - 00:10] (Visual: Teacher stands at the front of the classroom)

[00:10 - 00:15] student_A: Good morning, teacher!
```

#### 3. Clean Transcript JSON (`{video_id}_clean_transcript.json`)
Minimal JSON with only essential fields.

```json
{
  "video_id": "example_video",
  "duration_seconds": 1200.0,
  "total_entries": 150,
  "generated": "2024-01-01T12:00:00",
  "pipeline_configuration": {
    "chunk_duration": 300,
    "max_workers": 4,
    "model": "gemini-2.5-pro"
  },
  "transcript": [
    {
      "type": "utterance",
      "start_time": "00:00",
      "end_time": "00:05",
      "speaker": "teacher",
      "text": "Good morning, class!"
    }
  ]
}
```

## 🗂️ File Management System

### Automatic File Organization

The pipeline includes an advanced file management system that automatically:

- **Organizes videos** by date or type
- **Tracks file metadata** including size, hash, and processing status
- **Prevents duplicates** using file hashing
- **Manages cache** for faster reprocessing
- **Updates status** as videos are processed

### Data Directory Structure

```
data/
├── videos/                    # Video files
│   ├── raw/                  # Original videos
│   │   ├── 2024-01-15/      # Organized by date
│   │   └── lectures/         # Organized by type
│   └── processed/            # Processed videos
├── transcripts/              # Transcript outputs
│   ├── full/                # Complete JSON transcripts
│   ├── clean/               # Minimal JSON transcripts
│   └── text/                # Human-readable text
├── cache/                   # Processing cache
├── metadata/                # Video metadata
└── processed/               # Final outputs
```

### File Management Commands

```bash
# Set up data directory
python src/data/setup_data.py

# Add videos to management
python src/data/setup_data.py --add-video /path/to/video.mp4

# List managed videos
python src/data/setup_data.py --list-videos

# Export video list
python src/data/setup_data.py --export
```

## 💻 Programmatic Usage

### Basic Usage

```python
from src.transcription_pipeline import TranscriptionPipeline
from src.models import TranscriptionConfig

# Initialize pipeline
pipeline = TranscriptionPipeline(
    base_dir="outputs",
    data_dir="data",
    enable_file_management=True
)

# Create configuration
config = TranscriptionConfig(
    video_input="path/to/video.mp4",
    chunk_duration=300,
    max_workers=4,
    cleanup_uploaded_files=True
)

# Process video
results = pipeline.process_video(config)

print(f"Video ID: {results.video_id}")
print(f"Total entries: {len(results.full_transcript.transcript)}")
print(f"Cached: {results.cached}")
```

### Advanced Usage with File Management

```python
from src.core.file_manager import create_file_manager
from src.models import TranscriptionConfig, ModelType

# Initialize file manager
file_manager = create_file_manager("data", auto_organize=True)

# Add video to management
video_info = file_manager.add_video("path/to/video.mp4")

# Create configuration with file management
config = TranscriptionConfig(
    video_input=video_info['video_id'],  # Use video ID
    chunk_duration=300,
    max_workers=4,
    model=ModelType.GEMINI_2_5_PRO,
    cleanup_uploaded_files=True
)

# Process video
pipeline = TranscriptionPipeline(enable_file_management=True)
results = pipeline.process_video(config)

# Update status
file_manager.update_video_status(
    video_info['video_id'], 
    "transcribed",
    transcript_path=str(results.full_transcript)
)
```

### Batch Processing

```python
# Get all raw videos
raw_videos = file_manager.list_videos(status="raw")

# Process each video
for video in raw_videos:
    config = TranscriptionConfig(
        video_input=video['video_id'],
        chunk_duration=300,
        max_workers=4
    )
    
    results = pipeline.process_video(config)
    print(f"Processed: {results.video_id}")
```

## ⚙️ Configuration Options

### TranscriptionConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `video_input` | str | - | Video file path, ID, or filename |
| `chunk_duration` | int | 300 | Duration of each chunk in seconds |
| `max_workers` | int | 4 | Number of parallel workers |
| `cleanup_uploaded_files` | bool | True | Clean up uploaded files from Google |
| `force_reprocess` | bool | False | Force reprocessing even if cached |
| `model` | ModelType | GEMINI_2_5_PRO | AI model to use |
| `output_dir` | str | "outputs" | Output directory |
| `pipeline_version` | str | "1.0" | Pipeline version |

### Model Types

```python
from src.models import ModelType

# Available models
ModelType.GEMINI_2_5_PRO  # Default (recommended)
ModelType.GEMINI_1_5_PRO  # Alternative
```

## 📈 Performance Optimization

### Chunk Size Recommendations

| Video Length | Recommended Chunk Size | Reason |
|--------------|----------------------|--------|
| < 10 minutes | 300 seconds (5 min) | Faster processing |
| 10-30 minutes | 600 seconds (10 min) | Balanced performance |
| > 30 minutes | 900 seconds (15 min) | Fewer API calls |

### Worker Configuration

| System Type | Recommended Workers | Notes |
|-------------|-------------------|-------|
| CPU-bound | 2-4 workers | Limited by CPU cores |
| I/O-bound | 4-8 workers | Limited by network/disk |
| High-memory | 6-12 workers | Limited by RAM |

### Storage Requirements

```
Estimated storage needs:
- Raw videos: 1-5 GB per hour of video
- Transcripts: 1-10 MB per hour of video
- Cache: 100-500 MB per processing run
- Metadata: < 1 MB per video
```

## 🔍 Troubleshooting

### Common Issues

#### 1. API Key Not Found
```
ValueError: GOOGLE_API_KEY not found in environment variables
```
**Solution**: Set your Google API key:
```bash
export GOOGLE_API_KEY="your_api_key_here"
```

#### 2. File Upload Failures
```
Exception: Failed to upload file
```
**Solution**: Check file size limits and network connectivity.

#### 3. FFmpeg Not Found
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```
**Solution**: Install FFmpeg and ensure it's in your PATH.

#### 4. Import Errors
```
ImportError: attempted relative import beyond top-level package
```
**Solution**: Run from the project root directory and activate virtual environment.

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Issues

1. **Slow Processing**: Reduce chunk size or increase workers
2. **Memory Issues**: Reduce max_workers or chunk size
3. **API Rate Limits**: Reduce max_workers or add delays

## 📚 Examples

### Example 1: Basic Video Processing

```python
from src.transcription_pipeline import TranscriptionPipeline
from src.models import TranscriptionConfig

# Initialize pipeline
pipeline = TranscriptionPipeline("outputs")

# Process video
config = TranscriptionConfig(
    video_input="lecture.mp4",
    chunk_duration=300,
    max_workers=4
)

results = pipeline.process_video(config)
print(f"Transcript entries: {len(results.full_transcript.transcript)}")
```

### Example 2: File Management

```python
from src.core.file_manager import create_file_manager

# Initialize file manager
file_manager = create_file_manager("data")

# Add videos
video_info = file_manager.add_video("lecture.mp4")

# List videos
videos = file_manager.list_videos()
for video in videos:
    print(f"{video['video_id']}: {video['filename']} ({video['status']})")
```

### Example 3: Batch Processing

```python
# Process multiple videos
videos = file_manager.list_videos(status="raw")

for video in videos:
    config = TranscriptionConfig(video_input=video['video_id'])
    results = pipeline.process_video(config)
    file_manager.update_video_status(video['video_id'], "transcribed")
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is part of the BCI-Coding-1 repository. Please refer to the main repository for licensing information.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the examples in the `examples/` directory
3. Open an issue in the repository

## 🔄 Version History

- **v1.0**: Initial release with basic transcription
- **v1.1**: Added file management system
- **v1.2**: Enhanced parallel processing
- **v1.3**: Improved timestamp handling and caching

---

**Happy Transcribing! 🎬📝**