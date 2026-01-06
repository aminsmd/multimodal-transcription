# Terraform Configuration for Multimodal Transcription ECS Batch Processing

This Terraform configuration creates the necessary AWS resources to run the multimodal transcription batch processor as a scheduled ECS task.

## Resources Created

- **ECR Repository**: Docker image repository for the transcription service
- **ECS Cluster**: Container orchestration cluster
- **ECS Task Definition**: Configuration for running batch processing tasks
- **EventBridge Rule**: Scheduled cron job to trigger batch processing
- **IAM Roles**: Execution and task roles with appropriate permissions
- **CloudWatch Log Group**: Centralized logging for batch processing
- **EFS File System** (optional): Persistent storage for data and outputs

## Prerequisites

1. AWS CLI configured with the `bci` profile and appropriate credentials
2. Terraform >= 1.0 installed
3. Docker image pushed to ECR (see deployment workflow)
4. AWS Secrets Manager secret created for `GOOGLE_API_KEY`

## Setup

1. **Copy the example variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit `terraform.tfvars` with your specific values:**
   - Verify AWS profile is set to `bci` (default)
   - Update VPC, subnet, and security group IDs if needed
   - Adjust schedule expression if needed (default: 7am and 7pm UTC on weekdays)
   - Configure resource limits (CPU/memory)

3. **Initialize Terraform:**
   ```bash
   cd terraform
   terraform init
   ```

4. **Review the plan:**
   ```bash
   terraform plan
   ```

5. **Apply the configuration:**
   ```bash
   terraform apply
   ```

## Configuration

### Schedule Expression

The default schedule runs at 7am and 7pm UTC on weekdays (Monday-Friday). You can modify this in `terraform.tfvars`:

```hcl
schedule_expression = "cron(0 7,19 ? * MON-FRI *)"  # 7am and 7pm UTC on weekdays
```

Common cron patterns:
- `cron(0 7,19 ? * MON-FRI *)` - 7am and 7pm UTC on weekdays (default)
- `cron(0 2 * * ? *)` - Daily at 2 AM UTC
- `cron(0 */6 * * ? *)` - Every 6 hours
- `cron(0 0 * * ? *)` - Daily at midnight UTC
- `rate(1 hour)` - Every hour
- `rate(30 minutes)` - Every 30 minutes

**Note**: EventBridge uses UTC time. Adjust the hours if you need a different timezone.

### Resource Limits

Default configuration:
- CPU: 2048 (2 vCPU)
- Memory: 4096 MB (4 GB)

Adjust in `terraform.tfvars` based on your workload.

### EFS Storage

EFS is enabled by default for persistent storage. If you're using S3 instead, set:

```hcl
enable_efs = false
```

Note: If EFS is disabled, you'll need to update the task definition to use S3 for data and outputs.

## Task Definition Details

The batch processor runs with the following command:

```bash
python src/batch_processor.py \
  --database /app/data/video_database.json \
  --base-dir /app/outputs \
  --data-dir /app/data \
  --verbose
```

## Monitoring

### CloudWatch Logs

View logs in CloudWatch:
- Log Group: `/ecs/multimodal-transcription-batch`
- Log Stream: `ecs/multimodal-transcription-batch/<task-id>`

### ECS Console

Monitor task runs in the ECS console:
1. Navigate to the cluster: `multimodal-transcription-cluster`
2. View task history and status
3. Check task logs and metrics

### EventBridge

View scheduled executions:
1. Go to EventBridge → Rules
2. Find rule: `multimodal-transcription-batch-schedule`
3. View execution history and metrics

## Manual Task Execution

You can manually trigger a batch processing task:

```bash
aws ecs run-task \
  --cluster multimodal-transcription-cluster \
  --task-definition multimodal-transcription-batch \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-9b7957d7,subnet-e74bc28c,subnet-8135f2fc],securityGroups=[sg-0b638085b666a013f],assignPublicIp=ENABLED}"
```

## Troubleshooting

### Task Fails to Start

1. Check IAM roles have correct permissions
2. Verify ECR image exists and is accessible
3. Check security group allows outbound traffic
4. Verify secrets are accessible in Secrets Manager

### Task Runs But Fails

1. Check CloudWatch logs for errors
2. Verify GOOGLE_API_KEY secret is correct
3. Check EFS mount points (if enabled)
4. Verify database file exists in data directory

### Schedule Not Triggering

1. Check EventBridge rule is enabled
2. Verify IAM role has permissions to run ECS tasks
3. Check CloudWatch Events logs for errors

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all resources including EFS data (if not backed up).

## Integration with GitHub Actions

This Terraform configuration works alongside the GitHub Actions workflow in `.github/workflows/deploy-and-test.yml`. The workflow:

1. Builds and pushes Docker image to ECR
2. The Terraform-managed EventBridge rule triggers the task on schedule
3. Tasks run using the task definition created by Terraform

## Variables Reference

See `variables.tf` for all available variables and their descriptions.

