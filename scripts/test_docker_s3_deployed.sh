#!/bin/bash

# Test deployed functionality using Docker with S3 storage
# This simulates the deployed environment locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
S3_BUCKET="multimodal-transcription-videos-1761690600"
S3_VIDEO_PATH="test-videos/Adam_2024-03-03_6_32_PM.mp4"
S3_OUTPUT_PREFIX="deployed-test-outputs"
DOCKER_IMAGE="multimodal-transcription:latest"

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

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running"
        exit 1
    fi
    
    # Check if image exists
    if ! docker images | grep -q "$DOCKER_IMAGE"; then
        print_error "Docker image $DOCKER_IMAGE not found"
        print_info "Building image..."
        docker build -t $DOCKER_IMAGE .
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

# Function to test S3 access
test_s3_access() {
    print_info "Testing S3 access..."
    
    # Test if video exists in S3
    if ! aws s3 ls "s3://$S3_BUCKET/$S3_VIDEO_PATH" >/dev/null 2>&1; then
        print_error "Video file s3://$S3_BUCKET/$S3_VIDEO_PATH does not exist"
        exit 1
    fi
    
    print_success "S3 access confirmed"
}

# Function to run Docker test
run_docker_test() {
    print_info "Running deployed functionality test with Docker..."
    
    # Create output directory in S3
    aws s3api put-object --bucket $S3_BUCKET --key "$S3_OUTPUT_PREFIX/test-started.txt" --body /dev/null
    
    # Run the Docker container with S3 configuration
    print_info "Starting Docker container with S3 video and output..."
    
    docker run --rm \
        -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
        -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
        -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
        -e AWS_DEFAULT_REGION="us-east-2" \
        $DOCKER_IMAGE \
        python src/transcription_pipeline.py \
        --input "s3://$S3_BUCKET/$S3_VIDEO_PATH" \
        --output-dir "s3://$S3_BUCKET/$S3_OUTPUT_PREFIX" \
        --chunk-size 120 \
        --max-workers 2 \
        --verbose
    
    if [ $? -eq 0 ]; then
        print_success "Docker test completed successfully!"
    else
        print_error "Docker test failed!"
        return 1
    fi
}

# Function to check results
check_results() {
    print_info "Checking S3 output files..."
    
    # List files in S3 output directory
    aws s3 ls "s3://$S3_BUCKET/$S3_OUTPUT_PREFIX/" --recursive || {
        print_warning "No output files found in S3"
        return 0
    }
    
    print_success "S3 output files listed above"
}

# Main execution
print_info "Testing Deployed Functionality with Docker + S3"
print_info "==============================================="

# Check prerequisites
check_prerequisites

# Test S3 access
test_s3_access

# Run Docker test
if run_docker_test; then
    print_success "Deployed functionality test completed successfully!"
    
    # Check results
    check_results
    
    print_info "Test completed! Check the S3 bucket for output files:"
    print_info "  s3://$S3_BUCKET/$S3_OUTPUT_PREFIX/"
else
    print_error "Deployed functionality test failed!"
    exit 1
fi
