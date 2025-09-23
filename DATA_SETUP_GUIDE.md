# Data Directory Setup Guide

This guide helps you set up a proper data directory structure for organizing your videos and managing transcription pipeline outputs.

## Quick Start

```bash
# Set up the data directory structure
python data_setup.py --organize

# Add a video to your data directory
python data_setup.py --add-video /path/to/your/video.mp4

# List all videos
python data_setup.py --list-videos

# Export video list to CSV
python data_setup.py --export
```

## Recommended Directory Structure

```
data/
├── 📁 videos/                    # Video files
│   ├── 📁 raw/                  # Original video files
│   │   ├── 📁 2024-01-15/      # Organized by date
│   │   ├── 📁 2024-01-16/
│   │   └── 📁 lectures/         # Organized by type
│   └── 📁 processed/            # Processed videos
├── 📁 transcripts/              # Transcript outputs
│   ├── 📁 full/               # Complete transcript JSON
│   ├── 📁 clean/              # Minimal transcript JSON
│   └── 📁 text/               # Human-readable text
├── 📁 cache/                   # Processing cache
├── 📁 metadata/               # Video metadata
└── 📁 processed/              # Final outputs
```

## Video Organization Strategies

### 1. By Date (Recommended)
Organize videos by the date they were added or recorded:
```
videos/raw/2024-01-15/lecture_math.mp4
videos/raw/2024-01-15/lecture_science.mp4
videos/raw/2024-01-16/discussion.mp4
```

### 2. By Type/Category
Organize by content type or subject:
```
videos/raw/lectures/math_101_week1.mp4
videos/raw/lectures/science_201_week2.mp4
videos/raw/discussions/group_work.mp4
videos/raw/presentations/student_presentations.mp4
```

### 3. By Project
Organize by specific projects or courses:
```
videos/raw/project_alpha/meeting_1.mp4
videos/raw/project_alpha/meeting_2.mp4
videos/raw/course_math101/lecture_1.mp4
videos/raw/course_math101/lecture_2.mp4
```

## Video File Naming Conventions

### Recommended Naming Pattern
```
{date}_{type}_{subject}_{session}.{extension}
```

Examples:
- `2024-01-15_lecture_math_week1.mp4`
- `2024-01-16_discussion_science_group1.mp4`
- `2024-01-17_presentation_physics_final.mp4`

### Alternative Patterns
```
{subject}_{date}_{type}.{extension}
{project}_{session}_{date}.{extension}
{course}_{week}_{type}.{extension}
```

## Batch Processing Setup

### 1. Create Video Categories
```python
from data_setup import DataManager

dm = DataManager("data")

# Organize videos by type
video_types = {
    "lectures": ["video_id_1", "video_id_2"],
    "discussions": ["video_id_3", "video_id_4"],
    "presentations": ["video_id_5"]
}

dm.organize_by_type(video_types)
```

### 2. Batch Configuration
```python
# Create batch processing configuration
config_template = {
    "chunk_duration": 300,
    "max_workers": 4,
    "cleanup_uploaded_files": True,
    "force_reprocess": False
}

batch_config = dm.create_batch_config(
    video_ids=["video_1", "video_2", "video_3"],
    config_template=config_template
)
```

## Video Quality and Format Recommendations

### Supported Formats
- **MP4** (recommended)
- **MOV**
- **AVI**
- **MKV**
- **WebM**

### Quality Guidelines
- **Resolution**: 720p minimum, 1080p recommended
- **Frame Rate**: 24-30 fps
- **Audio**: Clear audio quality, avoid background noise
- **Duration**: 5-60 minutes per video (longer videos will be chunked)

### File Size Guidelines
- **Small videos** (< 100 MB): Process quickly
- **Medium videos** (100-500 MB): Standard processing
- **Large videos** (> 500 MB): May require more processing time

## Storage Management

### Disk Space Planning
```
Estimated storage needs:
- Raw videos: 1-5 GB per hour of video
- Transcripts: 1-10 MB per hour of video
- Cache: 100-500 MB per processing run
- Metadata: < 1 MB per video
```

### Cleanup Strategies
```python
# Clean up old cache files (older than 30 days)
dm.cleanup_old_files(days_old=30)

# Export video list for backup
csv_file = dm.export_video_list()
```

## Integration with Transcription Pipeline

### 1. Process Single Video
```python
from data_setup import DataManager
from models import TranscriptionConfig
from transcription_pipeline import TranscriptionPipeline

# Initialize data manager
dm = DataManager("data")

# Get video path
video_id = "your_video_id"
video_path = dm.get_video_path(video_id)

# Create configuration
config = TranscriptionConfig(
    video_input=str(video_path),
    chunk_duration=300,
    max_workers=4
)

# Process video
pipeline = TranscriptionPipeline("outputs")
results = pipeline.process_video(config)

# Update video status
dm.update_video_status(video_id, "transcribed", 
                      transcript_path=str(results.full_transcript))
```

### 2. Batch Processing
```python
# Process multiple videos
videos = dm.list_videos(status="raw")

for video in videos:
    video_path = dm.get_video_path(video['video_id'])
    
    config = TranscriptionConfig(
        video_input=str(video_path),
        chunk_duration=300,
        max_workers=4
    )
    
    results = pipeline.process_video(config)
    dm.update_video_status(video['video_id'], "transcribed")
```

## Best Practices

### 1. File Organization
- Use consistent naming conventions
- Organize by date or type, not both
- Keep original files in `raw/` directory
- Move processed files to `processed/` directory

### 2. Metadata Management
- Each video gets a unique ID
- Metadata includes file hash for deduplication
- Track processing status and timestamps
- Maintain processing history

### 3. Backup Strategy
- Keep original video files backed up
- Export video lists regularly
- Store transcripts in version control
- Use cloud storage for large files

### 4. Performance Optimization
- Use SSD storage for better performance
- Keep cache directory on fast storage
- Monitor disk space usage
- Clean up old files regularly

## Troubleshooting

### Common Issues

1. **Video not found**
   ```bash
   # Check if video exists
   python data_setup.py --list-videos
   ```

2. **Disk space issues**
   ```bash
   # Clean up old files
   python data_setup.py --cleanup
   ```

3. **Duplicate videos**
   - The system uses file hashes to detect duplicates
   - Check metadata for file hash matches

4. **Processing errors**
   - Check video format compatibility
   - Verify file permissions
   - Check disk space availability

### Getting Help

```bash
# Show all available options
python data_setup.py --help

# Check directory structure
python data_setup.py --organize

# List all videos with details
python data_setup.py --list-videos
```

## Example Workflow

1. **Set up data directory**
   ```bash
   python data_setup.py --organize
   ```

2. **Add videos**
   ```bash
   python data_setup.py --add-video /path/to/video1.mp4
   python data_setup.py --add-video /path/to/video2.mp4
   ```

3. **List and verify**
   ```bash
   python data_setup.py --list-videos
   ```

4. **Process videos**
   ```python
   # Use the transcription pipeline with your organized videos
   ```

5. **Export results**
   ```bash
   python data_setup.py --export
   ```

This setup provides a robust foundation for managing your video data and transcription pipeline outputs!
