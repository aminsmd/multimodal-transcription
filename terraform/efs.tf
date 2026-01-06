# EFS File System for persistent storage
resource "aws_efs_file_system" "app" {
  count = var.enable_efs ? 1 : 0

  creation_token = "${var.app_name}-efs"
  encrypted      = true

  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"

  tags = merge(var.tags, {
    Name = "${var.app_name}-efs"
  })
}

# EFS Mount Targets in each subnet
resource "aws_efs_mount_target" "app" {
  count = var.enable_efs ? length(var.subnet_ids) : 0

  file_system_id  = aws_efs_file_system.app[0].id
  subnet_id       = var.subnet_ids[count.index]
  security_groups = [aws_security_group.efs[0].id]
}

# EFS Access Point for data directory
resource "aws_efs_access_point" "data" {
  count = var.enable_efs ? 1 : 0

  file_system_id = aws_efs_file_system.app[0].id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/data"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  tags = merge(var.tags, {
    Name = "${var.app_name}-efs-data-access-point"
  })
}

# EFS Access Point for outputs directory
resource "aws_efs_access_point" "outputs" {
  count = var.enable_efs ? 1 : 0

  file_system_id = aws_efs_file_system.app[0].id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/outputs"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  tags = merge(var.tags, {
    Name = "${var.app_name}-efs-outputs-access-point"
  })
}

# IAM policy for EFS access (attached to execution role for mounting)
# ECS uses the execution role to mount EFS volumes
resource "aws_iam_role_policy" "ecs_task_execution_efs" {
  count = var.enable_efs ? 1 : 0

  name = "${var.app_name}-batch-task-execution-efs"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess"
        ]
        Resource = aws_efs_file_system.app[0].arn
        Condition = {
          StringEquals = {
            "elasticfilesystem:AccessPointArn" = aws_efs_access_point.data[0].arn
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess"
        ]
        Resource = aws_efs_file_system.app[0].arn
        Condition = {
          StringEquals = {
            "elasticfilesystem:AccessPointArn" = aws_efs_access_point.outputs[0].arn
          }
        }
      }
    ]
  })
}

