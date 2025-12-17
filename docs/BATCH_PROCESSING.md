# Batch Transcription Processing

This document describes the batch transcription processing functionality that automatically fetches videos from an API, downloads them from S3, transcribes them, and sends notifications.

## Overview

The batch transcription processor (`src/batch_transcription_processor.py`) automates the entire transcription workflow:

1. **Fetches videos** from the API endpoint that need transcription
2. **Downloads videos** from S3 bucket
3. **Processes each video** through the transcription pipeline
4. **Sends notifications** with success/error status and output directory

## Components

### 1. Video Fetcher (`src/api/video_fetcher.py`)

Fetches the list of videos that need transcription from the API endpoint:
- Endpoint: `https://886hed58x9.execute-api.us-east-1.amazonaws.com/prod/api/v1/files/paths/toTranscribe`
- Returns a list of video paths or video information objects

### 2. S3 Utilities (`src/utils/s3_utils.py`)

Utilities for working with S3:
- `extract_bucket_name_from_url()`: Extracts bucket name from various URL formats
- `construct_s3_url()`: Constructs full S3 URLs from bucket and path
- `download_video_from_s3()`: Downloads videos from S3 to local filesystem
- `get_s3_bucket_path()`: Gets S3 bucket path from environment variable

### 3. Notification Client (Updated)

The notification client (`src/api/notification_client.py`) has been updated to include:
- `output_directory` parameter in notifications
- Support for sending pipeline output directory with success/error notifications

### 4. Batch Processor (`src/batch_transcription_processor.py`)

Main orchestrator that coordinates all components.

## Usage

### Command Line

```bash
# Set required environment variables
export GOOGLE_API_KEY="your_api_key_here"
export S3_BUCKET_PATH="https://us-east-1.console.aws.amazon.com/s3/buckets/bci-prod-upload?region=us-east-1"

# Run batch processor
python src/batch_transcription_processor.py

# With custom options
python src/batch_transcription_processor.py \
  --chunk-size 600 \
  --max-workers 4 \
  --output-dir outputs \
  --data-dir data
```

### Programmatic Usage

```python
from src.batch_transcription_processor import BatchTranscriptionProcessor

# Initialize processor
processor = BatchTranscriptionProcessor(
    s3_bucket_path=None,  # Reads from S3_BUCKET_PATH env var
    output_dir="outputs",
    data_dir="data",
    chunk_duration=300,
    max_workers=4
)

# Process all videos
summary = processor.process_all_videos()

print(f"Total: {summary['total_videos']}")
print(f"Succeeded: {summary['succeeded']}")
print(f"Failed: {summary['failed']}")
```

## Environment Variables

### Required

- `GOOGLE_API_KEY`: Google API key for Gemini transcription
- `S3_BUCKET_PATH`: S3 bucket path (can be console URL, S3 URI, or bucket name)

### Optional

- `AWS_ACCESS_KEY_ID`: AWS access key (if not using IAM role)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (if not using IAM role)
- `AWS_DEFAULT_REGION`: AWS region (default: us-east-1)

## S3 Bucket Path Formats

The `S3_BUCKET_PATH` environment variable supports multiple formats:

1. **Console URL**: `https://us-east-1.console.aws.amazon.com/s3/buckets/bci-prod-upload?region=us-east-1`
2. **S3 URI**: `s3://bci-prod-upload`
3. **Bucket Name**: `bci-prod-upload`
4. **HTTPS URL**: `https://bci-prod-upload.s3.us-east-1.amazonaws.com`

The utility will automatically extract the bucket name from any of these formats.

## API Response Format

The video fetcher expects the API to return the following format:

```json
{
  "paths": [
    {
      "id": "69189bf37fcd33a6edc1e9ee",
      "path": "68dc488aac9091f3e8574f6f/SAS_and_SSS_Triangle_Congruence_CRITERIA.mp4"
    },
    {
      "id": "6925043f5f26ae5b7ecb805f",
      "path": "68a4f2686b650268b6ff1750/Law_of_Exponents.mp4"
    }
  ]
}
```

Each object in the `paths` array contains:
- `id`: The video ID (used for notifications)
- `path`: The S3 path to the video file (relative to the bucket root)

The processor will also handle alternative formats for backward compatibility:
- Array of strings: `["path/to/video1.mp4", ...]`
- Array of objects with different key names
- Object with `videos`, `data`, or `files` keys

## Notification Format

Notifications are sent to the API endpoint with the following format:

**Success:**
```json
{
  "videoId": "video_id_here",
  "status": "Completed",
  "outputDirectory": "/path/to/output/directory"
}
```

**Error:**
```json
{
  "videoId": "video_id_here",
  "status": "Error",
  "error": "Error message here",
  "outputDirectory": "/path/to/output/directory"
}
```

## Output Structure

The batch processor creates output directories following the standard pipeline structure:

```
outputs/
└── pipeline_runs/
    └── transcription_run_YYYYMMDD_HHMMSS/
        ├── videos/              # Original video files
        ├── chunks/               # Video chunks
        ├── transcripts/          # Generated transcripts
        ├── cache/                # Processing cache
        └── logs/                 # Log files
```

## Error Handling

The batch processor handles errors gracefully:

1. **API Fetch Errors**: Logs error and returns empty list
2. **S3 Download Errors**: Sends error notification and continues with next video
3. **Transcription Errors**: Sends error notification with error details
4. **Notification Errors**: Logs warning but doesn't fail the process

Each video is processed independently, so one failure doesn't stop the entire batch.

## Logging

The batch processor uses Python's logging module with INFO level by default. Logs include:
- Video fetching status
- S3 download progress
- Transcription progress
- Notification status
- Summary statistics

## Example Output

```
2024-01-15 10:30:00 - INFO - Fetching videos to transcribe from API...
2024-01-15 10:30:01 - INFO - Found 3 videos to transcribe
2024-01-15 10:30:01 - INFO - Processing video 1/3
2024-01-15 10:30:01 - INFO - Downloading s3://bci-prod-upload/videos/video1.mp4 to /tmp/video1.mp4...
2024-01-15 10:30:05 - INFO - ✅ Successfully downloaded video to /tmp/video1.mp4
2024-01-15 10:30:05 - INFO - Starting transcription for video1...
2024-01-15 10:35:20 - INFO - ✅ Successfully transcribed video1
2024-01-15 10:35:20 - INFO - Notification sent: {'success': True, ...}
...
======================================================================
BATCH PROCESSING SUMMARY
======================================================================
Total videos: 3
Succeeded: 3
Failed: 0
Output directory: outputs/pipeline_runs/transcription_run_20240115_103000
```

## Integration with GitHub Actions

The batch processor can be integrated into GitHub Actions workflows:

```yaml
- name: Run batch transcription
  env:
    GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
    S3_BUCKET_PATH: ${{ secrets.S3_BUCKET_PATH }}
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
  run: |
    python src/batch_transcription_processor.py \
      --chunk-size 600 \
      --max-workers 4
```

## Troubleshooting

### No videos found
- Check API endpoint is accessible
- Verify API response format matches expected structure
- Check network connectivity

### S3 download failures
- Verify `S3_BUCKET_PATH` is set correctly
- Check AWS credentials are configured
- Verify video paths exist in S3 bucket
- Check IAM permissions for S3 access

### Notification failures
- Verify notification endpoint is accessible
- Check video ID format matches API expectations
- Review notification API response for errors

