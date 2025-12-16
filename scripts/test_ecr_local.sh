#!/bin/bash

# Test ECR image locally (simulates deployed environment)
# This works with your current permissions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
S3_BUCKET="multimodal-transcription-videos-1761690600"
ECR_IMAGE="669655810547.dkr.ecr.us-east-2.amazonaws.com/multimodal-transcription:latest"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running"
        exit 1
    fi
    
    # Check if GOOGLE_API_KEY is set
    if [ -z "$GOOGLE_API_KEY" ]; then
        print_error "GOOGLE_API_KEY environment variable is not set"
        print_info "Please set your Google API key:"
        print_info "  export GOOGLE_API_KEY='your_api_key_here'"
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# Function to pull ECR image
pull_ecr_image() {
    print_info "Pulling ECR image..."
    
    # Login to ECR
    aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 669655810547.dkr.ecr.us-east-2.amazonaws.com
    
    # Pull the image
    docker pull $ECR_IMAGE
    
    print_success "ECR image pulled successfully"
}

# Function to run test
run_test() {
    local video_choice=$1
    local video_path=""
    local video_name=""
    
    # Set video path based on choice
    case "$video_choice" in
        "adam")
            video_path="test-videos/Adam_2024-03-03_6_32_PM.mp4"
            video_name="Adam"
            ;;
        "angela")
            video_path="test-videos/Angela_2025-03-10_2_11_PM.mp4"
            video_name="Angela"
            ;;
        "audrey")
            video_path="test-videos/Audrey_2025-04-06_6_20_PM-2.mp4"
            video_name="Audrey"
            ;;
        *)
            print_error "Invalid video choice: $video_choice"
            exit 1
            ;;
    esac
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local output_prefix="local-test-outputs/$video_name-$timestamp"
    
    print_info "Running test with ECR image..."
    print_info "🎬 Video: $video_name"
    print_info "📁 Output: s3://$S3_BUCKET/$output_prefix/"
    
    # Run the ECR container
    docker run --rm \
        -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
        -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
        -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
        -e AWS_DEFAULT_REGION="us-east-2" \
        $ECR_IMAGE \
        python src/transcription_pipeline.py \
        --input "s3://$S3_BUCKET/$video_path" \
        --output-dir "s3://$S3_BUCKET/$output_prefix" \
        --chunk-size 60 \
        --max-workers 2 \
        --verbose
    
    if [ $? -eq 0 ]; then
        print_success "Test completed successfully!"
        
        # List output files
        print_info "📋 S3 Output files:"
        aws s3 ls "s3://$S3_BUCKET/$output_prefix/" --recursive || echo "No files found"
        
        print_info "🔗 View results: https://s3.console.aws.amazon.com/s3/buckets/$S3_BUCKET/$output_prefix/"
    else
        print_error "Test failed!"
        return 1
    fi
}

# Function to show help
show_help() {
    echo "ECR Local Test Script"
    echo ""
    echo "Usage: $0 [VIDEO_CHOICE]"
    echo ""
    echo "Video choices:"
    echo "  adam    - Adam_2024-03-03_6_32_PM.mp4"
    echo "  angela  - Angela_2025-03-10_2_11_PM.mp4"
    echo "  audrey  - Audrey_2025-04-06_6_20_PM-2.mp4"
    echo ""
    echo "Environment variables needed:"
    echo "  GOOGLE_API_KEY - Your Google API key"
    echo "  AWS_ACCESS_KEY_ID - Your AWS access key"
    echo "  AWS_SECRET_ACCESS_KEY - Your AWS secret key"
    echo ""
    echo "Examples:"
    echo "  $0 adam"
    echo "  $0 angela"
    echo "  $0 audrey"
}

# Main execution
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

VIDEO_CHOICE=${1:-adam}

print_info "ECR Local Test - Deployed Environment Simulation"
print_info "================================================"

# Check prerequisites
check_prerequisites

# Pull ECR image
pull_ecr_image

# Run test
run_test "$VIDEO_CHOICE"

print_success "All tests completed!"
