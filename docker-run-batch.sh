#!/bin/bash

# Docker batch processing helper script
# This script builds and runs the batch transcription processor

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DOCKER_COMPOSE_FILE="docker-compose-batch.yml"
IMAGE_NAME="multimodal-transcription-batch"
CONTAINER_NAME="multimodal-transcription-batch"

# Function to print colored output
print_info() {
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

# Function to show help
show_help() {
    echo "Docker Batch Processing Helper Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h              Show this help message"
    echo "  --build, -b             Force rebuild Docker image"
    echo "  --no-cache              Build without cache"
    echo "  --max-videos N          Maximum videos to process per run"
    echo "  --no-file-management    Disable file management"
    echo "  --no-validation         Disable transcript validation"
    echo "  --verbose, -v           Enable verbose logging"
    echo "  --interactive, -i       Run in interactive mode"
    echo "  --cleanup               Clean up containers and images"
    echo ""
    echo "Examples:"
    echo "  $0                      # Run batch processing"
    echo "  $0 --build              # Force rebuild and run"
    echo "  $0 --max-videos 2       # Process maximum 2 videos"
    echo "  $0 --interactive        # Run in interactive mode"
    echo "  $0 --cleanup            # Clean up Docker resources"
}

# Function to check if GOOGLE_API_KEY is set
check_api_key() {
    if [ -z "$GOOGLE_API_KEY" ]; then
        print_error "GOOGLE_API_KEY environment variable is not set"
        print_info "Please set your Google API key:"
        print_info "  export GOOGLE_API_KEY='your_api_key_here'"
        exit 1
    fi
    print_success "Google API key is set"
}

# Function to check if database exists
check_database() {
    if [ ! -f "data/video_database.json" ]; then
        print_error "Video database not found: data/video_database.json"
        print_info "Please create the database file first"
        exit 1
    fi
    print_success "Video database found"
}

# Function to build Docker image
build_image() {
    local no_cache=$1
    
    print_info "Building Docker image..."
    
    local build_cmd="docker-compose -f $DOCKER_COMPOSE_FILE build"
    if [ "$no_cache" = true ]; then
        build_cmd="$build_cmd --no-cache"
    fi
    
    if eval $build_cmd; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Function to run batch processing
run_batch() {
    local max_videos=$1
    local no_file_management=$2
    local no_validation=$3
    local verbose=$4
    local interactive=$5
    
    print_info "Starting batch processing..."
    
    # Build command
    local cmd="docker-compose -f $DOCKER_COMPOSE_FILE run --rm"
    
    if [ "$interactive" = true ]; then
        cmd="$cmd batch-transcription bash"
    else
        cmd="$cmd batch-transcription python src/batch_processor.py"
        cmd="$cmd --database /app/data/video_database.json"
        cmd="$cmd --base-dir /app/outputs"
        cmd="$cmd --data-dir /app/data"
        
        if [ -n "$max_videos" ]; then
            cmd="$cmd --max-videos $max_videos"
        fi
        
        if [ "$no_file_management" = true ]; then
            cmd="$cmd --no-file-management"
        fi
        
        if [ "$no_validation" = true ]; then
            cmd="$cmd --no-validation"
        fi
        
        if [ "$verbose" = true ]; then
            cmd="$cmd --verbose"
        fi
    fi
    
    print_info "Running command: $cmd"
    
    if eval $cmd; then
        print_success "Batch processing completed successfully"
    else
        print_error "Batch processing failed"
        exit 1
    fi
}

# Function to cleanup Docker resources
cleanup() {
    print_info "Cleaning up Docker resources..."
    
    # Stop and remove containers
    docker-compose -f $DOCKER_COMPOSE_FILE down --remove-orphans 2>/dev/null || true
    
    # Remove images
    docker rmi $IMAGE_NAME 2>/dev/null || true
    
    # Remove unused images
    docker image prune -f
    
    print_success "Cleanup completed"
}

# Function to show database status
show_database_status() {
    if [ -f "data/video_database.json" ]; then
        print_info "Database status:"
        python3 -c "
import json
with open('data/video_database.json', 'r') as f:
    data = json.load(f)
stats = data['database_info']
print(f'  Total videos: {stats[\"total_videos\"]}')
print(f'  Pending: {stats[\"pending_videos\"]}')
print(f'  Processed: {stats[\"processed_videos\"]}')
print(f'  Failed: {stats[\"failed_videos\"]}')
"
    else
        print_warning "Database file not found"
    fi
}

# Parse command line arguments
BUILD=false
NO_CACHE=false
MAX_VIDEOS=""
NO_FILE_MANAGEMENT=false
NO_VALIDATION=false
VERBOSE=false
INTERACTIVE=false
CLEANUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --build|-b)
            BUILD=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --max-videos)
            MAX_VIDEOS="$2"
            shift 2
            ;;
        --no-file-management)
            NO_FILE_MANAGEMENT=true
            shift
            ;;
        --no-validation)
            NO_VALIDATION=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --interactive|-i)
            INTERACTIVE=true
            shift
            ;;
        --cleanup)
            CLEANUP=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
print_info "Multimodal Transcription Batch Processor"
print_info "========================================"

if [ "$CLEANUP" = true ]; then
    cleanup
    exit 0
fi

# Check prerequisites
check_api_key
check_database

# Show database status
show_database_status

# Build image if requested or if it doesn't exist
if [ "$BUILD" = true ] || ! docker images | grep -q "$IMAGE_NAME"; then
    build_image $NO_CACHE
fi

# Run batch processing
run_batch "$MAX_VIDEOS" $NO_FILE_MANAGEMENT $NO_VALIDATION $VERBOSE $INTERACTIVE

print_success "Script completed successfully"
