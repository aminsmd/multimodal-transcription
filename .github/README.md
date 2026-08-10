# GitHub Actions for Multimodal Transcription

Workflows for deploying and testing the multimodal transcription pipeline on AWS ECS/ECR.

## Workflows

### 1. Deploy to ECS (`.github/workflows/deploy.yml`) — stage & prod

- **Triggers**:
  - Push to `stage` → deploy **stage** (`:stage` image)
  - Push to `main` → deploy **prod** (`:latest` image)
  - Manual (`workflow_dispatch`) with environment choice
- **Purpose**: Build and push the Docker image to ECR for the selected environment
- **Image tags**:
  - `stage` branch / env → `multimodal-transcription:stage` (ECS family `multimodal-transcription-stage-batch`)
  - `main` branch / `prod` env → `multimodal-transcription:latest` (ECS family `multimodal-transcription-batch`)
- Also tags the image with the commit SHA for traceability
- Optional (manual only): sync `GOOGLE_API_KEY` into AWS Secrets Manager (`google-api-key`)

S3 buckets and API URLs are **not** GitHub secrets — they are set on the ECS task definition by Terraform (`stage.tfvars` / `terraform.tfvars`).

### 2. Deploy and Test (`.github/workflows/deploy-and-test.yml`)

- **Trigger**: Manual
- **Purpose**: Ad-hoc single-video or batch test runs (not the primary stage/prod deploy path)
- Builds an image tagged with the commit SHA and runs an ECS Fargate task

## Required GitHub setup

### 1. Create Environments

In **Settings → Environments**, create:

| Environment | Notes |
|-------------|--------|
| `stage` | Optional protection rules |
| `prod` | Recommended: required reviewers before deploy |

The deploy workflow sets `environment:` to the selected input so protection rules apply.

### 2. Secrets

Stage and prod share one AWS account, one ECR repo, and one Secrets Manager key. Put these on **each** environment (`stage` and `prod`), **or** as repository secrets (both environments inherit repo secrets).

| Secret | Required for | Description |
|--------|----------------|-------------|
| `AWS_ACCESS_KEY_ID` | Deploy + Deploy-and-test | IAM user/key that can push ECR, describe ECS, and (if syncing) manage Secrets Manager |
| `AWS_SECRET_ACCESS_KEY` | Deploy + Deploy-and-test | Matching secret key |
| `GOOGLE_API_KEY` | Deploy (only if “sync” enabled) + Deploy-and-test | Gemini API key; synced to AWS Secrets Manager as `google-api-key` |

#### Optional (Deploy and Test only)

| Secret | Description |
|--------|-------------|
| `S3_BUCKET_PATH` | Source bucket override for ad-hoc tests |

#### S3 buckets (by environment)

| Environment | S3 bucket |
|-------------|-----------|
| `stage` | `bci-multimodal-transcripts-stage` |
| `prod` | `bci-multimodal-transcripts-prod` |

These are set on the ECS task definition by Terraform (`S3_DEST_BUCKET`). They are not GitHub secrets unless you also want them for ad-hoc test workflows.

Other env-specific config (not GitHub secrets):

| Config | Stage | Prod |
|--------|-------|------|
| ECR tag | `stage` | `latest` |
| Video fetcher / notification URLs | stage API Gateway | prod API Gateway |

### IAM permissions the deploy key needs

Minimum useful set:

- `ecr:*` (or push/pull/auth for `multimodal-transcription`)
- `ecs:DescribeTaskDefinition`
- `secretsmanager:DescribeSecret`, `GetSecretValue`, `PutSecretValue`, `CreateSecret` (only if syncing the Google key)
- `sts:GetCallerIdentity`

## Usage

### Deploy stage or prod

**Automatic**
- Merge/push to `stage` → builds batch image and pushes ECR `:stage`
- Merge/push to `main` → builds batch image and pushes ECR `:latest`

**Manual**
1. Actions → **Deploy to ECS** → **Run workflow**
2. Choose `stage` or `prod`
3. Optionally enable sync of `GOOGLE_API_KEY`
4. Confirm the job summary shows the pushed tag and digest

Next EventBridge schedule (or a manual `aws ecs run-task`) pulls the updated image. Infra/env-var changes still go through Terraform (`terraform/README.md`).

### Ad-hoc test run

Use **Deploy and Test** with single/batch mode and a video selection or custom path.

## Monitoring

- **GitHub Actions**: run logs and job summary
- **ECS**: cluster `multimodal-transcription-cluster`
- **CloudWatch**: `/ecs/multimodal-transcription-batch` (prod), `/ecs/multimodal-transcription-stage-batch` (stage)

## Troubleshooting

1. **Missing AWS credentials** — Ensure `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` exist on the environment (or as repo secrets).
2. **Task definition not found** — Apply Terraform for that workspace first (`stage` + `stage.tfvars`, or prod tfvars).
3. **Wrong API/S3 behavior after deploy** — Image-only deploy does not change env vars; update Terraform and re-apply.
4. **GOOGLE_API_KEY sync fails** — Set the secret on the same GitHub Environment used for the run.
