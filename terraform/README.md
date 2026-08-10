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
   - Optionally override S3 buckets and API endpoint URLs (defaults are production)

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

## Stage Environment

Stage runs as a **separate ECS stack** on the same cluster and ECR repository as production. Resource names are namespaced via `app_name = "multimodal-transcription-stage"`.

### Prerequisites

Create (or confirm) these S3 buckets before applying stage — Terraform does not create them:

- Source: `bci-stage-upload` (typically us-east-1)
- Destination: `bci-multimodal-transcripts-stage`

### Workspace isolation

Use Terraform workspaces so stage and prod state stay separate (required when using local state):

```bash
cd terraform
terraform init

# One-time: move existing default state into a prod workspace (if you already applied prod)
terraform workspace new prod
# Or, if default already holds prod: terraform workspace select default && terraform workspace new stage

terraform workspace new stage
terraform workspace select stage
```

### Apply stage

```bash
cp stage.tfvars.example stage.tfvars
# Edit stage.tfvars if needed

terraform workspace select stage
terraform plan -var-file=stage.tfvars
terraform apply -var-file=stage.tfvars
```

Stage task definition family: `multimodal-transcription-stage-batch`  
Stage EventBridge rule: `multimodal-transcription-stage-batch-schedule`  
Shared cluster: `multimodal-transcription-cluster`  
Stage image tag: `stage` (prod keeps `:latest` — push to `:stage` only when deploying stage)

### Build and push stage image

```bash
AWS_REGION=us-east-2
ECR_REGISTRY=669655810547.dkr.ecr.us-east-2.amazonaws.com
REPO=multimodal-transcription

aws ecr get-login-password --region "$AWS_REGION" --profile bci \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

docker build --platform linux/amd64 -t "$ECR_REGISTRY/$REPO:stage" .
docker push "$ECR_REGISTRY/$REPO:stage"
```

### Stage container env (from tfvars)

| Variable | Stage value |
|----------|-------------|
| `S3_BUCKET_PATH` | `bci-stage-upload` |
| `S3_DEST_BUCKET` | `bci-multimodal-transcripts-stage` |
| `VIDEO_FETCHER_URL` | `https://nv6ktiaxob.execute-api.us-east-1.amazonaws.com/stage/api/v1/files/paths/toTranscribe` |
| `NOTIFICATION_API_URL` | `https://nv6ktiaxob.execute-api.us-east-1.amazonaws.com/stage/api/v1/pipeline/aiTranscription-Complete` |

### Manual stage task run

```bash
aws ecs run-task \
  --cluster multimodal-transcription-cluster \
  --task-definition multimodal-transcription-stage-batch \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-9b7957d7,subnet-e74bc28c,subnet-8135f2fc],securityGroups=[sg-0b638085b666a013f],assignPublicIp=ENABLED}" \
  --profile bci \
  --region us-east-2
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
python src/batch_transcription_processor.py \
  --output-dir /app/outputs \
  --data-dir /app/data
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

## Updating the Google API Key Secret

To update the `GOOGLE_API_KEY` secret in AWS Secrets Manager:

### Using AWS CLI

1. **Update the secret value:**
   ```bash
   aws secretsmanager update-secret \
     --secret-id google-api-key \
     --secret-string "YOUR_NEW_API_KEY" \
     --profile bci \
     --region us-east-2
   ```

2. **Verify the update:**
   ```bash
   aws secretsmanager get-secret-value \
     --secret-id google-api-key \
     --profile bci \
     --region us-east-2 \
     --query SecretString \
     --output text
   ```

**Note**: If you're using a different secret name (configured in `terraform.tfvars`), replace `google-api-key` with your actual secret name.

### Using AWS Console

1. Navigate to **AWS Secrets Manager** in the AWS Console
2. Find the secret named `google-api-key` (or your configured secret name)
3. Click on the secret to open it
4. Click **Retrieve secret value** → **Edit**
5. Enter your new API key value
6. Click **Save**

### After Updating

- The secret update takes effect immediately
- New ECS tasks will automatically use the updated secret value
- No Terraform changes or task definition updates are required
- Existing running tasks will continue using the old value until they restart

## Troubleshooting

### Task Fails to Start

1. Check IAM roles have correct permissions
2. Verify ECR image exists and is accessible
3. Check security group allows outbound traffic
4. Verify secrets are accessible in Secrets Manager

### Task Runs But Fails

1. Check CloudWatch logs for errors
2. Verify GOOGLE_API_KEY secret is correct (see "Updating the Google API Key Secret" above)
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

