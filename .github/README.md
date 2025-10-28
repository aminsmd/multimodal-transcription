# GitHub Actions for Multimodal Transcription

This repository includes several GitHub Actions workflows for building, testing, and deploying the multimodal transcription pipeline.

## Workflows Overview

### 1. Docker Build and Test (`.github/workflows/docker-test.yml`)
- **Triggers**: Push to main/develop, pull requests, manual dispatch
- **Purpose**: Build and test Docker images
- **Features**:
  - Builds Docker image with buildx
  - Tests image can run help command
  - Optional batch processing test with dry run
  - Security scanning with Trivy
  - Caching for faster builds

### 2. Batch Processing (`.github/workflows/batch-processing.yml`)
- **Triggers**: Manual dispatch, scheduled (daily at 2 AM UTC), push to main/develop
- **Purpose**: Run batch video processing
- **Features**:
  - Builds and pushes Docker image to GitHub Container Registry
  - Runs batch processing locally or in Docker
  - Uploads results as artifacts
  - Supports configurable max videos per run

### 3. ECS Deployment (`.github/workflows/ecs-deploy.yml`)
- **Triggers**: Manual dispatch, push to main
- **Purpose**: Deploy to AWS ECS for production batch processing
- **Features**:
  - Builds and pushes to Amazon ECR
  - Deploys ECS task definition
  - Runs batch processing as ECS task
  - Cleans up old ECR images

## Required Secrets

Configure these secrets in your GitHub repository settings:

### Required for All Workflows
- `GOOGLE_API_KEY`: Your Google API key for Gemini AI

### Required for ECS Deployment
- `AWS_ACCESS_KEY_ID`: AWS access key for ECR and ECS
- `AWS_SECRET_ACCESS_KEY`: AWS secret key for ECR and ECS

## Usage

### Manual Batch Processing
1. Go to Actions tab in GitHub
2. Select "Batch Video Processing"
3. Click "Run workflow"
4. Configure parameters:
   - Max videos to process
   - Force reprocessing (if needed)

### Scheduled Processing
The workflow runs automatically every day at 2 AM UTC. To modify the schedule, edit the cron expression in `batch-processing.yml`:

```yaml
schedule:
  - cron: '0 2 * * *'  # Daily at 2 AM UTC
```

### ECS Deployment
1. Set up AWS credentials as secrets
2. Update `ecs-task-definition.json` with your AWS account details
3. Run the "ECS Batch Processing Deployment" workflow
4. Configure ECS cluster, service, and task definition

## Configuration

### Video Database
The batch processor reads from `data/video_database.json`. This file should contain:
- Video metadata (file paths, processing config)
- Status tracking (pending, processing, completed, failed)
- Priority ordering

### Docker Configuration
- Base image: `python:3.11-slim`
- Includes FFmpeg for video processing
- Runs as non-root user for security
- Exposes port 8000 (for future web interface)

### ECS Task Definition
- CPU: 2048 (2 vCPU)
- Memory: 4096 MB (4 GB)
- Uses EFS for persistent storage
- Supports both data and outputs volumes

## Monitoring

### GitHub Actions
- View workflow runs in the Actions tab
- Check logs for processing details
- Download artifacts for results

### ECS (if deployed)
- Monitor tasks in ECS console
- Check CloudWatch logs for `/ecs/batch-transcription`
- Set up CloudWatch alarms for failures

## Troubleshooting

### Common Issues

1. **API Key Not Set**
   - Ensure `GOOGLE_API_KEY` secret is configured
   - Check secret name matches exactly

2. **Docker Build Fails**
   - Check Dockerfile syntax
   - Verify all dependencies in requirements.txt
   - Review build logs for specific errors

3. **Batch Processing Fails**
   - Verify video files exist in `data/videos/`
   - Check database JSON format
   - Review processing logs for API errors

4. **ECS Deployment Fails**
   - Verify AWS credentials are correct
   - Check ECS task definition JSON
   - Ensure EFS file systems exist
   - Verify IAM roles have correct permissions

### Debug Mode
Enable verbose logging by adding `--verbose` to batch processor commands in the workflows.

## Customization

### Adding New Triggers
Edit the `on:` section in workflow files to add new triggers:

```yaml
on:
  push:
    branches: [ main, develop ]
    paths: [ 'src/**' ]  # Only trigger on source changes
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
```

### Modifying Processing Parameters
Update the batch processor command in workflows:

```yaml
python src/batch_processor.py \
  --database /app/data/video_database.json \
  --base-dir /app/outputs \
  --data-dir /app/data \
  --max-videos 5 \
  --chunk-duration 600 \
  --max-workers 8 \
  --verbose
```

### Adding Notifications
Add notification steps to workflows:

```yaml
- name: Notify on Success
  uses: 8398a7/action-slack@v3
  with:
    status: success
    text: 'Batch processing completed successfully!'
  if: success()

- name: Notify on Failure
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    text: 'Batch processing failed!'
  if: failure()
```