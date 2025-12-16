# Docker Setup for Multimodal Transcription Pipeline

This guide explains how to run the multimodal transcription pipeline using Docker containers.

## 🐳 Quick Start

### Prerequisites

- Docker installed
- Google API Key for Gemini
- Video files to process

### 1. Environment Setup

Set your Google API key:

```bash
export GOOGLE_API_KEY="your_api_key_here"
```

### 2. Build and Run

#### Option A: Using the Helper Script (Recommended)

```bash
# Make the helper script executable
chmod +x docker-run.sh

# Process a video (automatically builds image if needed)
./docker-run.sh data/videos/your_video.mp4

# Process with custom settings
./docker-run.sh data/videos/your_video.mp4 --chunk-size 600 --max-workers 4

# Force reprocessing
./docker-run.sh data/videos/your_video.mp4 --force-reprocess
```

#### Option B: Direct Docker Commands

```bash
# Build the Docker image
docker build -t multimodal-transcription .

# Run the pipeline
docker run --rm \
  -v "$(pwd)/data/videos:/app/data/videos:ro" \
  -v "$(pwd)/outputs:/app/outputs" \
  -v "$(pwd)/data:/app/data" \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  multimodal-transcription \
  python src/transcription_pipeline.py \
  --input /app/data/videos/your_video.mp4 \
  --chunk-size 300 \
  --max-workers 2 \
  --data-dir /app/data \
  --output-dir /app/outputs \
  --no-file-management
```

## 📁 Directory Structure

```
multimodal-transcription/
├── Dockerfile                 # Docker image definition
├── docker-compose.yml        # Docker Compose configuration
├── docker-entrypoint.sh     # Entrypoint script
├── .dockerignore            # Files to exclude from Docker context
├── .env                     # Environment variables
├── data/
│   └── videos/              # Input videos (mounted as read-only)
├── outputs/                 # Output transcripts (mounted as volume)
└── logs/                    # Log files (mounted as volume)
```

## 🚀 Usage Examples

### Basic Usage

```bash
# Process a single video
docker run --rm \
  -v "$(pwd)/data/videos:/app/data/videos:ro" \
  -v "$(pwd)/outputs:/app/outputs" \
  -v "$(pwd)/data:/app/data" \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  multimodal-transcription \
  python src/transcription_pipeline.py \
  --input /app/data/videos/lecture.mp4 \
  --no-file-management
```

### Advanced Usage

```bash
# Process with custom settings
docker run --rm \
  -v "$(pwd)/data/videos:/app/data/videos:ro" \
  -v "$(pwd)/outputs:/app/outputs" \
  -v "$(pwd)/data:/app/data" \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  multimodal-transcription \
  python src/transcription_pipeline.py \
  --input /app/data/videos/lecture.mp4 \
  --chunk-size 600 \
  --max-workers 8 \
  --force-reprocess \
  --no-file-management
```

### Interactive Mode

```bash
# Run container interactively
docker run --rm -it \
  -v "$(pwd)/data/videos:/app/data/videos:ro" \
  -v "$(pwd)/outputs:/app/outputs" \
  -v "$(pwd)/data:/app/data" \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  multimodal-transcription \
  bash

# Inside container, run pipeline manually
python src/transcription_pipeline.py --input /app/data/videos/lecture.mp4 --no-file-management
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google API key for Gemini | Required |
| `CHUNK_SIZE` | Default chunk size in seconds | 300 |
| `MAX_WORKERS` | Default number of workers | 4 |

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input` | Path to input video file | Required |
| `--chunk-size` | Duration of each chunk in seconds | 300 |
| `--max-workers` | Number of parallel workers | 4 |
| `--data-dir` | Data directory for file management | /app/data |
| `--output-dir` | Output directory | /app/outputs |
| `--no-file-management` | Disable file management | false |
| `--force-reprocess` | Force reprocessing | false |
| `--no-cleanup` | Skip cleanup of uploaded files | false |

## 📊 Volume Mounts

### Input Videos
- **Host**: `./data/videos/`
- **Container**: `/app/data/videos/`
- **Access**: Read-only
- **Purpose**: Place your input video files here

### Outputs
- **Host**: `./outputs/`
- **Container**: `/app/outputs/`
- **Access**: Read-write
- **Purpose**: Generated transcripts and processing results

### Data Directory
- **Host**: `./data/`
- **Container**: `/app/data/`
- **Access**: Read-write
- **Purpose**: File management and metadata storage

### Logs
- **Host**: `./logs/`
- **Container**: `/app/logs/`
- **Access**: Read-write
- **Purpose**: Processing logs and debug information

## 🛠️ Development

### Building Custom Image

```bash
# Build with custom tag
docker build -t multimodal-transcription:custom .

# Run with custom image
docker run --rm \
  -e GOOGLE_API_KEY=your_key \
  -v $(pwd)/data/videos:/app/data/videos:ro \
  -v $(pwd)/outputs:/app/outputs \
  multimodal-transcription:custom \
  --input /app/data/videos/lecture.mp4
```

### Debugging

```bash
# Run with debug output
docker-compose run --rm transcription-pipeline \
  --input /app/data/videos/lecture.mp4 \
  --chunk-size 60 \
  --max-workers 1

# Check container logs
docker-compose logs transcription-pipeline

# Access container shell
docker-compose exec transcription-pipeline bash
```

## 🔍 Monitoring

### Web Interface

The docker-compose.yml includes an optional web interface:

```bash
# Start web interface
docker-compose up web-interface

# Access at http://localhost:8000
```

### Log Monitoring

```bash
# Follow logs in real-time
docker-compose logs -f transcription-pipeline

# View specific log files
docker-compose exec transcription-pipeline tail -f /app/logs/transcription.log
```

## 🚨 Troubleshooting

### Common Issues

#### 1. API Key Not Set
```
Error: GOOGLE_API_KEY environment variable is required
```
**Solution**: Set your Google API key in the `.env` file or environment:
```bash
export GOOGLE_API_KEY="your_api_key_here"
```

#### 2. Video File Not Found
```
Error: Input video file not found: /app/data/videos/lecture.mp4
```
**Solution**: Ensure your video file is in the `data/videos/` directory:
```bash
mkdir -p data/videos
cp your_video.mp4 data/videos/
```

#### 3. Permission Denied
```
Error: Permission denied
```
**Solution**: Check file permissions and ownership:
```bash
chmod 755 data/videos/your_video.mp4
```

#### 4. Out of Memory
```
Error: Container killed due to memory limit
```
**Solution**: Increase memory limits in docker-compose.yml or reduce max_workers:
```yaml
deploy:
  resources:
    limits:
      memory: 8G  # Increase from 4G
```

### Debug Commands

```bash
# Check container status
docker-compose ps

# View container resource usage
docker stats multimodal-transcription

# Check container logs
docker-compose logs transcription-pipeline

# Inspect container
docker-compose exec transcription-pipeline ps aux
```

## 📈 Performance Optimization

### Resource Limits

Adjust resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 8G      # Increase for large videos
      cpus: '4.0'     # Increase for faster processing
    reservations:
      memory: 4G      # Minimum memory
      cpus: '2.0'     # Minimum CPUs
```

### Parallel Processing

```bash
# Process multiple videos in parallel
for video in data/videos/*.mp4; do
  docker-compose run --rm transcription-pipeline \
    --input "/app/data/videos/$(basename "$video")" &
done
wait
```

### Caching

The pipeline automatically caches results. To force reprocessing:

```bash
docker-compose run --rm transcription-pipeline \
  --input /app/data/videos/lecture.mp4 \
  --force-reprocess
```

## 🔒 Security

### Non-Root User

The Docker image runs as a non-root user (`appuser`) for security.

### API Key Security

Never commit your `.env` file to version control:

```bash
# Add to .gitignore
echo ".env" >> .gitignore
```

### Network Security

The container doesn't expose unnecessary ports. Only the optional web interface uses port 8000.

## 📚 Examples

### Example 1: Single Video Processing

```bash
# Place video in data/videos/
cp lecture.mp4 data/videos/

# Process video
docker run --rm \
  -v "$(pwd)/data/videos:/app/data/videos:ro" \
  -v "$(pwd)/outputs:/app/outputs" \
  -v "$(pwd)/data:/app/data" \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  multimodal-transcription \
  python src/transcription_pipeline.py \
  --input /app/data/videos/lecture.mp4 \
  --no-file-management

# Check results
ls -la outputs/pipeline_runs/
```

### Example 2: Batch Processing

```bash
#!/bin/bash
# Process all videos in data/videos/
for video in data/videos/*.mp4; do
  echo "Processing: $video"
  docker run --rm \
    -v "$(pwd)/data/videos:/app/data/videos:ro" \
    -v "$(pwd)/outputs:/app/outputs" \
    -v "$(pwd)/data:/app/data" \
    -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
    multimodal-transcription \
    python src/transcription_pipeline.py \
    --input "/app/data/videos/$(basename "$video")" \
    --chunk-size 300 \
    --max-workers 4 \
    --no-file-management
done
```

### Example 3: Custom Configuration

```bash
# Create custom docker-compose override
cat > docker-compose.override.yml << EOF
version: '3.8'
services:
  transcription-pipeline:
    environment:
      - CHUNK_SIZE=600
      - MAX_WORKERS=8
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
EOF

# Run with custom configuration
docker-compose up transcription-pipeline
```

## 🧹 Cleanup

### Remove Containers and Images

```bash
# Stop and remove containers
docker-compose down

# Remove images
docker-compose down --rmi all

# Clean up volumes (WARNING: This removes all data)
docker-compose down -v
```

### Clean Up Outputs

```bash
# Remove old pipeline runs
rm -rf outputs/pipeline_runs/transcription_run_*

# Clean up logs
rm -rf logs/*
```

## 📞 Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the main README.md for general usage
3. Check container logs: `docker-compose logs transcription-pipeline`
4. Open an issue in the repository

---

**Happy Docker Transcribing! 🐳📝**
