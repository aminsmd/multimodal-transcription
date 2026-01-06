# ECR Push Scripts

Scripts to help build and push Docker images to Amazon ECR.

## Quick Start

### Using the Script

```bash
# From the multimodal-transcription directory
./scripts/push-to-ecr.sh [tag]

# Examples:
./scripts/push-to-ecr.sh           # Uses "latest" tag
./scripts/push-to-ecr.sh v1.0.0    # Uses "v1.0.0" tag
./scripts/push-to-ecr.sh $(git rev-parse --short HEAD)  # Uses git commit hash
```

### Manual Commands

If you prefer to run commands manually:

```bash
# Set variables
export AWS_PROFILE="bci"
export AWS_REGION="us-east-2"
export ECR_REPOSITORY="multimodal-transcription"
export IMAGE_TAG="latest"

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Login to ECR
aws ecr get-login-password --profile $AWS_PROFILE --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_REGISTRY

# Build the image
docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .

# Tag for ECR
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_REPOSITORY}:latest

# Push to ECR
docker push ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
docker push ${ECR_REGISTRY}/${ECR_REPOSITORY}:latest
```

## Prerequisites

1. AWS CLI configured with `bci` profile
2. Docker installed and running
3. Appropriate IAM permissions to push to ECR

## Troubleshooting

### Authentication Errors

If you get authentication errors:
```bash
# Verify your AWS profile
aws sts get-caller-identity --profile bci

# Re-authenticate
aws ecr get-login-password --profile bci --region us-east-2 | \
    docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-2.amazonaws.com
```

### Repository Not Found

The script will automatically create the repository if it doesn't exist. If you get permission errors, ensure your AWS profile has `ecr:CreateRepository` permission.

### Build Errors

Make sure you're running the script from the `multimodal-transcription` directory (where the Dockerfile is located).

