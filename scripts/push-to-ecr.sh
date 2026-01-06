#!/bin/bash
# Script to build and push Docker image to ECR
# Uses the bci AWS profile

set -e

# Configuration
AWS_PROFILE="bci"
AWS_REGION="us-east-2"
ECR_REPOSITORY="multimodal-transcription"
IMAGE_TAG="${1:-latest}"  # Use first argument as tag, default to "latest"

# Get AWS account ID
echo "🔍 Getting AWS account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Failed to get AWS account ID. Check your AWS profile: $AWS_PROFILE"
    exit 1
fi

echo "✅ AWS Account ID: $AWS_ACCOUNT_ID"

# Construct ECR repository URL
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPOSITORY_URL="${ECR_REGISTRY}/${ECR_REPOSITORY}"

echo "📦 ECR Repository: $ECR_REPOSITORY_URL"
echo "🏷️  Image Tag: $IMAGE_TAG"

# Login to ECR
echo "🔐 Logging in to Amazon ECR..."
aws ecr get-login-password --profile $AWS_PROFILE --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_REGISTRY

# Check if repository exists, create if it doesn't
echo "🔍 Checking if ECR repository exists..."
if ! aws ecr describe-repositories --profile $AWS_PROFILE --region $AWS_REGION --repository-names $ECR_REPOSITORY &>/dev/null; then
    echo "📝 Creating ECR repository..."
    aws ecr create-repository \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --repository-name $ECR_REPOSITORY \
        --image-scanning-configuration scanOnPush=true \
        --image-tag-mutability MUTABLE
    echo "✅ Repository created"
else
    echo "✅ Repository already exists"
fi

# Build the Docker image for linux/amd64 platform (required for ECS Fargate)
# Using docker buildx for reliable cross-platform builds
echo "🔨 Building Docker image for linux/amd64 platform (ECS Fargate requirement)..."

# Ensure buildx is available and create a builder if needed
if ! docker buildx ls | grep -q "multibuilder"; then
    echo "📦 Creating buildx builder..."
    docker buildx create --name multibuilder --use 2>/dev/null || docker buildx use multibuilder 2>/dev/null || true
fi

# Build using buildx for linux/amd64
DIR_NAME=$(basename "$(pwd)")
COMPOSE_IMAGE_NAME="${DIR_NAME}_batch-transcription"

echo "🔨 Building with buildx for linux/amd64..."
docker buildx build \
    --platform linux/amd64 \
    --load \
    -f Dockerfile \
    -t ${COMPOSE_IMAGE_NAME}:latest \
    .

echo "✅ Image built successfully for linux/amd64 platform"

# Verify the image exists, try alternative naming if needed
if ! docker image inspect ${COMPOSE_IMAGE_NAME}:latest &>/dev/null; then
    # Try lowercase version (docker-compose sometimes lowercases)
    COMPOSE_IMAGE_NAME_LOWER=$(echo "${COMPOSE_IMAGE_NAME}" | tr '[:upper:]' '[:lower:]')
    if docker image inspect ${COMPOSE_IMAGE_NAME_LOWER}:latest &>/dev/null; then
        COMPOSE_IMAGE_NAME=${COMPOSE_IMAGE_NAME_LOWER}
    else
        echo "❌ Failed to find built image: ${COMPOSE_IMAGE_NAME}:latest"
        echo "💡 Trying to find the image that was just built..."
        # Find the most recently created image with batch-transcription in the name
        FOUND_IMAGE=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -i "batch-transcription" | head -1)
        if [ -n "$FOUND_IMAGE" ]; then
            echo "✅ Found image: $FOUND_IMAGE"
            COMPOSE_IMAGE_NAME=$(echo "$FOUND_IMAGE" | cut -d: -f1)
        else
            echo "💡 Available images:"
            docker images | head -10
            exit 1
        fi
    fi
fi

echo "✅ Using image: ${COMPOSE_IMAGE_NAME}:latest"

# Tag the image for ECR
echo "🏷️  Tagging image for ECR..."
docker tag ${COMPOSE_IMAGE_NAME}:latest ${ECR_REPOSITORY_URL}:${IMAGE_TAG}

# Also tag as latest if using a different tag
if [ "$IMAGE_TAG" != "latest" ]; then
    echo "🏷️  Also tagging as latest..."
    docker tag ${COMPOSE_IMAGE_NAME}:latest ${ECR_REPOSITORY_URL}:latest
fi

# Push the image
echo "📤 Pushing image to ECR..."
docker push ${ECR_REPOSITORY_URL}:${IMAGE_TAG}

if [ "$IMAGE_TAG" != "latest" ]; then
    echo "📤 Pushing latest tag..."
    docker push ${ECR_REPOSITORY_URL}:latest
fi

echo "✅ Successfully pushed ${ECR_REPOSITORY_URL}:${IMAGE_TAG}"
echo "🎉 Image is now available in ECR!"

