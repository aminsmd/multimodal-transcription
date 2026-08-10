variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

variable "aws_profile" {
  description = "AWS profile to use for authentication"
  type        = string
  default     = "bci"
}

variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "multimodal-transcription"
}

variable "vpc_id" {
  description = "VPC ID for ECS tasks"
  type        = string
  default     = "vpc-f2452499"
}

variable "subnet_ids" {
  description = "List of subnet IDs for ECS tasks"
  type        = list(string)
  default     = ["subnet-9b7957d7", "subnet-e74bc28c", "subnet-8135f2fc"]
}

variable "security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
  default     = "sg-0b638085b666a013f"
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "multimodal-transcription"
}

variable "ecr_image_tag" {
  description = "ECR image tag for the ECS task (use 'stage' for stage, 'latest' for prod)"
  type        = string
  default     = "latest"
}

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
  default     = "multimodal-transcription-cluster"
}

variable "cpu" {
  description = "CPU units for the ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 2048 # 2 vCPU
}

variable "memory" {
  description = "Memory for the ECS task in MB"
  type        = number
  default     = 4096 # 4 GB
}

variable "google_api_key_secret_name" {
  description = "Name of the secret in AWS Secrets Manager for GOOGLE_API_KEY"
  type        = string
  default     = "google-api-key"
}

variable "schedule_expression" {
  description = "EventBridge schedule expression (cron format)"
  type        = string
  default     = "cron(0 7,19 ? * MON-FRI *)" # 7am and 7pm UTC on weekdays
}

variable "enable_efs" {
  description = "Whether to enable EFS for persistent storage"
  type        = bool
  default     = true
}

variable "s3_bucket_path" {
  description = "S3 source bucket for reading input videos (S3_BUCKET_PATH)"
  type        = string
  default     = "bci-prod-upload"
}

variable "s3_dest_bucket" {
  description = "S3 destination bucket for uploading transcription outputs (S3_DEST_BUCKET)"
  type        = string
  default     = "bci-multimodal-transcripts-prod"
}

variable "s3_output_prefix" {
  description = "S3 key prefix for transcription outputs (S3_OUTPUT_PREFIX)"
  type        = string
  default     = "transcripts"
}

variable "video_fetcher_url" {
  description = "API endpoint for listing videos to transcribe (VIDEO_FETCHER_URL)"
  type        = string
  default     = "https://886hed58x9.execute-api.us-east-1.amazonaws.com/prod/api/v1/files/paths/toTranscribe"
}

variable "notification_api_url" {
  description = "API endpoint for transcription completion notifications (NOTIFICATION_API_URL)"
  type        = string
  default     = "https://886hed58x9.execute-api.us-east-1.amazonaws.com/prod/pipeline/aiTranscription-Complete"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "multimodal-transcription"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

