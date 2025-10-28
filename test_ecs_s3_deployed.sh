#!/bin/bash

# Test script for deployed ECS code with S3 storage
# This script runs a one-time ECS task to process a video with S3 storage

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="us-east-2"
S3_BUCKET="multimodal-transcription-videos-1761690600"
S3_VIDEO_PATH="test-videos/Adam_2024-03-03_6_32_PM.mp4"
S3_OUTPUT_PREFIX="deployed-test-outputs"
ECS_CLUSTER="multimodal-transcription-cluster"
ECS_TASK_DEFINITION="multimodal-transcription-batch-task"

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
    
    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS CLI is not configured or credentials are invalid"
        exit 1
    fi
    
    # Check if GOOGLE_API_KEY is set
    if [ -z "$GOOGLE_API_KEY" ]; then
        print_error "GOOGLE_API_KEY environment variable is not set"
        print_info "Please set your Google API key:"
        print_info "  export GOOGLE_API_KEY='your_api_key_here'"
        exit 1
    fi
    
    # Check if S3 bucket exists
    if ! aws s3 ls "s3://$S3_BUCKET" >/dev/null 2>&1; then
        print_error "S3 bucket $S3_BUCKET does not exist or is not accessible"
        exit 1
    fi
    
    # Check if video exists in S3
    if ! aws s3 ls "s3://$S3_BUCKET/$S3_VIDEO_PATH" >/dev/null 2>&1; then
        print_error "Video file s3://$S3_BUCKET/$S3_VIDEO_PATH does not exist"
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# Function to run ECS task
run_ecs_task() {
    print_info "Running ECS task for deployed testing..."
    
    # Create a temporary task definition with S3 configuration
    cat > temp-task-definition.json << EOF
{
  "family": "multimodal-transcription-batch-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::669655810547:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::669655810547:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "batch-transcription",
      "image": "669655810547.dkr.ecr.us-east-2.amazonaws.com/multimodal-transcription:latest",
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/batch-transcription",
          "awslogs-region": "us-east-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "environment": [
        {
          "name": "PYTHONUNBUFFERED",
          "value": "1"
        },
        {
          "name": "S3_BUCKET",
          "value": "$S3_BUCKET"
        },
        {
          "name": "S3_OUTPUT_PREFIX",
          "value": "$S3_OUTPUT_PREFIX"
        }
      ],
      "secrets": [
        {
          "name": "GOOGLE_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-2:669655810547:secret:google-api-key"
        }
      ],
      "command": [
        "python",
        "src/batch_processor.py",
        "--database", "/app/data/video_database.json",
        "--base-dir", "s3://$S3_BUCKET/$S3_OUTPUT_PREFIX",
        "--data-dir", "s3://$S3_BUCKET/data",
        "--max-videos", "1",
        "--verbose"
      ]
    }
  ]
}
EOF

    # Register the task definition
    print_info "Registering task definition..."
    TASK_DEF_ARN=$(aws ecs register-task-definition \
        --cli-input-json file://temp-task-definition.json \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)
    
    print_success "Task definition registered: $TASK_DEF_ARN"
    
    # Run the task
    print_info "Starting ECS task..."
    TASK_ARN=$(aws ecs run-task \
        --cluster $ECS_CLUSTER \
        --task-definition $TASK_DEF_ARN \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[subnet-9b7957d7,subnet-e74bc28c,subnet-8135f2fc],securityGroups=[sg-0b638085b666a013f],assignPublicIp=ENABLED}" \
        --query 'tasks[0].taskArn' \
        --output text)
    
    print_success "ECS task started: $TASK_ARN"
    
    # Wait for task to complete
    print_info "Waiting for task to complete..."
    aws ecs wait tasks-stopped \
        --cluster $ECS_CLUSTER \
        --tasks $TASK_ARN
    
    # Get task status
    TASK_STATUS=$(aws ecs describe-tasks \
        --cluster $ECS_CLUSTER \
        --tasks $TASK_ARN \
        --query 'tasks[0].lastStatus' \
        --output text)
    
    EXIT_CODE=$(aws ecs describe-tasks \
        --cluster $ECS_CLUSTER \
        --tasks $TASK_ARN \
        --query 'tasks[0].containers[0].exitCode' \
        --output text)
    
    if [ "$TASK_STATUS" = "STOPPED" ] && [ "$EXIT_CODE" = "0" ]; then
        print_success "ECS task completed successfully!"
    else
        print_error "ECS task failed with status: $TASK_STATUS, exit code: $EXIT_CODE"
        
        # Get task logs
        print_info "Fetching task logs..."
        aws logs get-log-events \
            --log-group-name "/ecs/batch-transcription" \
            --log-stream-name "ecs/batch-transcription/$TASK_ARN" \
            --start-from-head \
            --query 'events[*].message' \
            --output text | tail -20
    fi
    
    # Clean up temporary file
    rm -f temp-task-definition.json
    
    return $EXIT_CODE
}

# Function to list S3 output files
list_s3_outputs() {
    print_info "Listing S3 output files..."
    
    aws s3 ls "s3://$S3_BUCKET/$S3_OUTPUT_PREFIX/" --recursive || {
        print_warning "No output files found in S3"
        return 0
    }
    
    print_success "S3 output files listed above"
}

# Main execution
print_info "Testing Deployed ECS Code with S3 Storage"
print_info "=========================================="

# Check prerequisites
check_prerequisites

# Run ECS task
if run_ecs_task; then
    print_success "Deployed testing completed successfully!"
    
    # List S3 outputs
    list_s3_outputs
    
    print_info "Check the S3 bucket for output files:"
    print_info "  s3://$S3_BUCKET/$S3_OUTPUT_PREFIX/"
else
    print_error "Deployed testing failed!"
    exit 1
fi
