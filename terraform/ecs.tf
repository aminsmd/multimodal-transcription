# Data source for existing ECS Cluster
data "aws_ecs_cluster" "main" {
  cluster_name = var.ecs_cluster_name
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "batch_transcription" {
  name              = "/ecs/${var.app_name}-batch"
  retention_in_days = 7

  tags = var.tags
}

# ECS Task Execution Role (for pulling images, writing logs, etc.)
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.app_name}-batch-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Attach AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for Secrets Manager access
resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${var.app_name}-batch-task-execution-secrets"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.google_api_key_secret_name}*"
        ]
      }
    ]
  })
}

# ECS Task Role (for application-level permissions like S3 access)
resource "aws_iam_role" "ecs_task" {
  name = "${var.app_name}-batch-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Attach S3 full access policy for reading/writing video files
resource "aws_iam_role_policy_attachment" "ecs_task_s3" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Local variable for container definition with conditional mount points
locals {
  container_definition = merge(
    {
      name  = "${var.app_name}-batch"
      image = "${data.aws_ecr_repository.app.repository_url}:latest"

      environment = [
        {
          name  = "PYTHONUNBUFFERED"
          value = "1"
        },
        {
          name  = "AWS_DEFAULT_REGION"
          value = var.aws_region
        }
      ]

      secrets = [
        {
          name      = "GOOGLE_API_KEY"
          valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.google_api_key_secret_name}"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.batch_transcription.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      command = [
        "python",
        "src/batch_processor.py",
        "--database",
        "/app/data/video_database.json",
        "--base-dir",
        "/app/outputs",
        "--data-dir",
        "/app/data",
        "--verbose"
      ]

      essential = true
    },
    var.enable_efs ? {
      mountPoints = [
        {
          sourceVolume  = "efs-data"
          containerPath = "/app/data"
          readOnly      = false
        },
        {
          sourceVolume  = "efs-outputs"
          containerPath = "/app/outputs"
          readOnly      = false
        }
      ]
    } : {}
  )
}

# ECS Task Definition for Batch Processing
resource "aws_ecs_task_definition" "batch" {
  family                   = "${var.app_name}-batch"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([local.container_definition])

  # Add EFS volumes if enabled
  dynamic "volume" {
    for_each = var.enable_efs ? [1] : []
    content {
      name = "efs-data"

      efs_volume_configuration {
        file_system_id     = aws_efs_file_system.app[0].id
        root_directory     = "/"
        transit_encryption = "ENABLED"

        authorization_config {
          access_point_id = aws_efs_access_point.data[0].id
          iam             = "ENABLED"
        }
      }
    }
  }

  dynamic "volume" {
    for_each = var.enable_efs ? [1] : []
    content {
      name = "efs-outputs"

      efs_volume_configuration {
        file_system_id     = aws_efs_file_system.app[0].id
        root_directory     = "/"
        transit_encryption = "ENABLED"

        authorization_config {
          access_point_id = aws_efs_access_point.outputs[0].id
          iam             = "ENABLED"
        }
      }
    }
  }

  tags = var.tags
}

