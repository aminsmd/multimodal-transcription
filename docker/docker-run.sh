#!/bin/bash
# Docker helper script for multimodal transcription pipeline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to display usage
usage() {
    echo "Docker Helper for Multimodal Transcription Pipeline"
    echo ""
    echo "Usage: $0 [OPTIONS] VIDEO_FILE"
    echo ""
    echo "Options:"
    echo "  --chunk-size SECONDS   Duration of each chunk in seconds (default: 300)"
    echo "  --max-workers NUM      Number of parallel workers (default: 2)"
    echo "  --force-reprocess      Force reprocessing even if cached"
    echo "  --interactive          Run container interactively"
    echo "  --help                 Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  GOOGLE_API_KEY         Required: Your Google API key for Gemini"
    echo ""
    echo "Examples:"
    echo "  $0 data/videos/lecture.mp4"
    echo "  $0 data/videos/lecture.mp4 --chunk-size 600 --max-workers 4"
    echo "  $0 data/videos/lecture.mp4 --force-reprocess"
    echo "  $0 --interactive"
}

# Check if GOOGLE_API_KEY is set
if [ -z "$GOOGLE_API_KEY" ]; then
    print_error "GOOGLE_API_KEY environment variable is required"
    print_status "Please set your Google API key:"
    print_status "  export GOOGLE_API_KEY='your_api_key_here'"
    exit 1
fi

# Default values
VIDEO_FILE=""
CHUNK_SIZE=300
MAX_WORKERS=2
FORCE_REPROCESS=""
INTERACTIVE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --chunk-size)
            CHUNK_SIZE="$2"
            shift 2
            ;;
        --max-workers)
            MAX_WORKERS="$2"
            shift 2
            ;;
        --force-reprocess)
            FORCE_REPROCESS="--force-reprocess"
            shift
            ;;
        --interactive)
            INTERACTIVE="true"
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            if [ -z "$VIDEO_FILE" ]; then
                VIDEO_FILE="$1"
            else
                print_error "Multiple video files specified"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if video file is provided for non-interactive mode
if [ "$INTERACTIVE" != "true" ] && [ -z "$VIDEO_FILE" ]; then
    print_error "Video file is required for non-interactive mode"
    usage
    exit 1
fi

# Check if video file exists (for non-interactive mode)
if [ "$INTERACTIVE" != "true" ] && [ ! -f "$VIDEO_FILE" ]; then
    print_error "Video file not found: $VIDEO_FILE"
    exit 1
fi

# Build Docker image if it doesn't exist
if ! docker image inspect multimodal-transcription >/dev/null 2>&1; then
    print_status "Building Docker image..."
    docker build -t multimodal-transcription .
    print_success "Docker image built successfully!"
fi

# Create necessary directories
mkdir -p data/videos outputs logs

# Build the Docker command
DOCKER_CMD="docker run --rm"
DOCKER_CMD="$DOCKER_CMD -v \"$(pwd)/data/videos:/app/data/videos:ro\""
DOCKER_CMD="$DOCKER_CMD -v \"$(pwd)/outputs:/app/outputs\""
DOCKER_CMD="$DOCKER_CMD -v \"$(pwd)/data:/app/data\""
DOCKER_CMD="$DOCKER_CMD -e GOOGLE_API_KEY=\"$GOOGLE_API_KEY\""
DOCKER_CMD="$DOCKER_CMD multimodal-transcription"

if [ "$INTERACTIVE" = "true" ]; then
    print_status "Starting interactive container..."
    eval "$DOCKER_CMD -it bash"
else
    # Convert relative path to absolute path for container
    if [[ "$VIDEO_FILE" == /* ]]; then
        CONTAINER_VIDEO_PATH="$VIDEO_FILE"
    else
        CONTAINER_VIDEO_PATH="/app/data/videos/$(basename "$VIDEO_FILE")"
    fi
    
    # Copy video to data/videos if it's not already there
    if [ ! -f "data/videos/$(basename "$VIDEO_FILE")" ]; then
        print_status "Copying video to data/videos/..."
        cp "$VIDEO_FILE" "data/videos/"
    fi
    
    print_status "Processing video: $(basename "$VIDEO_FILE")"
    print_status "Chunk size: $CHUNK_SIZE seconds"
    print_status "Max workers: $MAX_WORKERS"
    
    # Build the transcription command
    TRANSCRIPTION_CMD="python src/transcription_pipeline.py"
    TRANSCRIPTION_CMD="$TRANSCRIPTION_CMD --input \"$CONTAINER_VIDEO_PATH\""
    TRANSCRIPTION_CMD="$TRANSCRIPTION_CMD --chunk-size $CHUNK_SIZE"
    TRANSCRIPTION_CMD="$TRANSCRIPTION_CMD --max-workers $MAX_WORKERS"
    TRANSCRIPTION_CMD="$TRANSCRIPTION_CMD --data-dir /app/data"
    TRANSCRIPTION_CMD="$TRANSCRIPTION_CMD --output-dir /app/outputs"
    TRANSCRIPTION_CMD="$TRANSCRIPTION_CMD --no-file-management"
    
    if [ -n "$FORCE_REPROCESS" ]; then
        TRANSCRIPTION_CMD="$TRANSCRIPTION_CMD $FORCE_REPROCESS"
    fi
    
    # Execute the command
    print_status "Executing: $DOCKER_CMD $TRANSCRIPTION_CMD"
    eval "$DOCKER_CMD $TRANSCRIPTION_CMD"
    
    print_success "Video processing completed!"
    print_status "Check outputs in: outputs/pipeline_runs/"
fi
