#!/bin/bash
set -e

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --input VIDEO_PATH     Path to input video file"
    echo "  --chunk-size SECONDS   Duration of each chunk in seconds (default: 300)"
    echo "  --max-workers NUM      Number of parallel workers (default: 4)"
    echo "  --data-dir PATH        Data directory for file management (default: /app/data)"
    echo "  --output-dir PATH      Output directory (default: /app/outputs)"
    echo "  --no-file-management   Disable file management"
    echo "  --force-reprocess       Force reprocessing even if cached"
    echo "  --no-cleanup           Skip cleanup of uploaded files"
    echo "  --help                 Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  GOOGLE_API_KEY         Required: Your Google API key for Gemini"
    echo ""
    echo "Examples:"
    echo "  $0 --input /app/data/videos/lecture.mp4"
    echo "  $0 --input /app/data/videos/lecture.mp4 --chunk-size 600 --max-workers 8"
    echo "  $0 --input /app/data/videos/lecture.mp4 --force-reprocess"
}

# Check if GOOGLE_API_KEY is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "Error: GOOGLE_API_KEY environment variable is required"
    echo "Please set your Google API key:"
    echo "  export GOOGLE_API_KEY='your_api_key_here'"
    exit 1
fi

# Default values
INPUT_VIDEO=""
CHUNK_SIZE=300
MAX_WORKERS=4
DATA_DIR="/app/data"
OUTPUT_DIR="/app/outputs"
NO_FILE_MANAGEMENT=""
FORCE_REPROCESS=""
NO_CLEANUP=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input)
            INPUT_VIDEO="$2"
            shift 2
            ;;
        --chunk-size)
            CHUNK_SIZE="$2"
            shift 2
            ;;
        --max-workers)
            MAX_WORKERS="$2"
            shift 2
            ;;
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --no-file-management)
            NO_FILE_MANAGEMENT="--no-file-management"
            shift
            ;;
        --force-reprocess)
            FORCE_REPROCESS="--force-reprocess"
            shift
            ;;
        --no-cleanup)
            NO_CLEANUP="--no-cleanup"
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if input video is provided
if [ -z "$INPUT_VIDEO" ]; then
    echo "Error: --input VIDEO_PATH is required"
    usage
    exit 1
fi

# Check if input video exists
if [ ! -f "$INPUT_VIDEO" ]; then
    echo "Error: Input video file not found: $INPUT_VIDEO"
    exit 1
fi

# Create necessary directories
mkdir -p "$DATA_DIR" "$OUTPUT_DIR" "$OUTPUT_DIR/pipeline_runs"

echo "Starting multimodal transcription pipeline..."
echo "Input video: $INPUT_VIDEO"
echo "Chunk size: $CHUNK_SIZE seconds"
echo "Max workers: $MAX_WORKERS"
echo "Data directory: $DATA_DIR"
echo "Output directory: $OUTPUT_DIR"

# Build the command
CMD="python src/transcription_pipeline.py \
    --input \"$INPUT_VIDEO\" \
    --chunk-size $CHUNK_SIZE \
    --max-workers $MAX_WORKERS \
    --data-dir \"$DATA_DIR\" \
    --output-dir \"$OUTPUT_DIR\""

# Add optional flags
if [ -n "$NO_FILE_MANAGEMENT" ]; then
    CMD="$CMD $NO_FILE_MANAGEMENT"
fi

if [ -n "$FORCE_REPROCESS" ]; then
    CMD="$CMD $FORCE_REPROCESS"
fi

if [ -n "$NO_CLEANUP" ]; then
    CMD="$CMD $NO_CLEANUP"
fi

# Execute the command
echo "Executing: $CMD"
eval $CMD

echo "Transcription pipeline completed!"
