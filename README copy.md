# Standalone Video Transcription Pipeline

A clean and focused video transcription pipeline that processes videos into detailed transcripts without segmentation. This pipeline is extracted from the main BCI-Coding-1 project and designed to work independently.

## Features

- **Video Processing**: Processes local video files
- **Parallel Transcription**: Uses parallel processing for faster transcript generation
- **Multimodal Analysis**: Uses Gemini 2.5 Pro for both audio and visual content analysis
- **Multiple Output Formats**: Generates JSON, text, and clean JSON outputs
- **No Segmentation**: Focuses purely on transcription without semantic segmentation
- **Caching**: Intelligent file upload caching to avoid re-uploading identical files

## Requirements

- Python 3.8+
- Google API Key for Gemini
- FFmpeg (for video processing)

## Installation

1. Clone or copy this directory to your desired location
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Google API key:
   ```bash
   export GOOGLE_API_KEY="your_api_key_here"
   ```
   Or create a `.env` file:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

## Usage

### Basic Usage

```bash
# Process a video file
python src/transcription_pipeline.py --input /path/to/video.mp4

# Custom chunk size and workers
python src/transcription_pipeline.py --input video.mp4 --chunk-size 600 --max-workers 8
```

### Command Line Arguments

- `--input`: Video file path (required)
- `--chunk-size`: Duration of each chunk in seconds (default: 300)
- `--max-workers`: Maximum number of parallel workers (default: 4)
- `--output-dir`: Output directory (default: outputs)

### Programmatic Usage

```python
from src.transcription_pipeline import TranscriptionPipeline

# Initialize pipeline
pipeline = TranscriptionPipeline("outputs")

# Process video
results = pipeline.process_video(
    video_input="path/to/video.mp4",
    chunk_duration=300,
    max_workers=4
)
```

## Output Structure

The pipeline creates a structured output directory:

```
outputs/
└── pipeline_runs/
    └── transcription_run_YYYYMMDD_HHMMSS/
        ├── videos/                    # Original video files
        ├── chunks/                    # Video chunks
        ├── transcripts/               # Transcript files
        │   ├── {video_id}_transcript.json
        │   ├── {video_id}_full_transcript.json
        │   ├── {video_id}_full_transcript.txt
        │   └── {video_id}_clean_transcript.json
        ├── cache/                     # Upload cache
        └── logs/                      # Log files
```

## Output Files

### 1. Full Transcript JSON (`{video_id}_full_transcript.json`)
Complete transcript with all metadata and timestamps.

### 2. Full Transcript Text (`{video_id}_full_transcript.txt`)
Human-readable text version of the transcript.

### 3. Clean Transcript JSON (`{video_id}_clean_transcript.json`)
Minimal JSON with only essential fields:
```json
{
  "video_id": "example",
  "duration_seconds": 1200,
  "total_entries": 150,
  "generated": "2024-01-01T12:00:00",
  "transcript": [
    {
      "type": "utterance",
      "start_time": "00:05",
      "end_time": "00:08",
      "speaker": "teacher",
      "text": "Good morning, class!"
    }
  ]
}
```

## Configuration

### Environment Variables

- `GOOGLE_API_KEY`: Required. Your Google API key for Gemini access.

### Chunk Size Recommendations

- **Small videos (< 10 minutes)**: 300 seconds (5 minutes)
- **Medium videos (10-30 minutes)**: 600 seconds (10 minutes)
- **Large videos (> 30 minutes)**: 900 seconds (15 minutes)

### Worker Configuration

- **CPU-bound tasks**: Use 2-4 workers
- **I/O-bound tasks**: Use 4-8 workers
- **High-memory systems**: Use 6-12 workers

## API Usage

The pipeline uses Google's Gemini 2.5 Pro model for multimodal analysis. Each chunk is processed with:

1. **Audio Analysis**: Speech recognition and speaker identification
2. **Visual Analysis**: Visual event detection and description
3. **Context Integration**: Maintains speaker consistency across chunks

## Error Handling

The pipeline includes robust error handling:

- **File Upload Failures**: Automatic retry with exponential backoff
- **API Rate Limits**: Built-in rate limiting and queuing
- **Chunk Processing Errors**: Individual chunk failures don't stop the pipeline
- **Network Issues**: Automatic retry for transient network problems

## Performance Tips

1. **Use appropriate chunk sizes**: Larger chunks reduce API calls but may hit size limits
2. **Optimize worker count**: Balance between speed and API rate limits
3. **Enable caching**: Reuse uploaded files to avoid re-uploading
4. **Monitor API usage**: Track your Google API quota and costs

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```
   ValueError: GOOGLE_API_KEY not found in environment variables
   ```
   Solution: Set your Google API key in environment variables or `.env` file.

2. **File Upload Failures**
   ```
   Exception: Failed to upload file
   ```
   Solution: Check file size limits and network connectivity.

3. **FFmpeg Not Found**
   ```
   FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
   ```
   Solution: Install FFmpeg and ensure it's in your PATH.

### Debug Mode

Enable verbose logging by modifying the pipeline:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

This project is part of the BCI-Coding-1 repository. Please refer to the main repository for licensing information.

## Contributing

This is a standalone extraction from the main BCI-Coding-1 project. For contributions, please refer to the main repository.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the main BCI-Coding-1 repository documentation
3. Open an issue in the main repository
