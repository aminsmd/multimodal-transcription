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

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "multimodal-transcription"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

