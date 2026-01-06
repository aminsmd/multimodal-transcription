# Security Group for EFS
# EFS needs a dedicated security group that allows NFS traffic from ECS tasks
resource "aws_security_group" "efs" {
  count = var.enable_efs ? 1 : 0

  name        = "${var.app_name}-efs-sg"
  description = "Security group for EFS mount targets"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    description     = "NFS from ECS tasks"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [var.security_group_id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.app_name}-efs-sg"
  })
}

