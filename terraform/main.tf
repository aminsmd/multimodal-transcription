terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = var.tags
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Get VPC information
data "aws_vpc" "main" {
  id = var.vpc_id
}

# Get subnet information
data "aws_subnets" "main" {
  filter {
    name   = "subnet-id"
    values = var.subnet_ids
  }
}

# Get security group
data "aws_security_group" "ecs_tasks" {
  id = var.security_group_id
}

