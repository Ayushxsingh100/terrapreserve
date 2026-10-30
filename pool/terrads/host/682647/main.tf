# AWS Platform Module
# Creates application platform: EKS, RDS, etc.
# This is a placeholder - extend based on your needs

terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# =============================================================================
# Local Variables
# =============================================================================

locals {
  common_tags = {
    Environment = var.environment
    Project     = var.project
    ManagedBy   = "terraform"
  }
}

# =============================================================================
# Security Group for Application
# =============================================================================

resource "aws_security_group" "app" {
  name        = "${var.project}-${var.environment}-app-sg"
  description = "Security group for application"
  vpc_id      = var.vpc_id

  # Egress: Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.environment}-app-sg"
  })
}

# =============================================================================
# Application Load Balancer (Optional - uncomment to use)
# =============================================================================

# resource "aws_lb" "app" {
#   name               = "${var.project}-${var.environment}-alb"
#   internal           = false
#   load_balancer_type = "application"
#   security_groups    = [aws_security_group.alb.id]
#   subnets            = var.public_subnet_ids
#
#   enable_deletion_protection = var.environment == "prd" ? true : false
#
#   tags = merge(local.common_tags, {
#     Name = "${var.project}-${var.environment}-alb"
#   })
# }

# =============================================================================
# EKS Cluster (Optional - uncomment to use)
# =============================================================================

# module "eks" {
#   source  = "terraform-aws-modules/eks/aws"
#   version = "~> 20.0"
#
#   cluster_name    = "${var.project}-${var.environment}"
#   cluster_version = "1.29"
#
#   vpc_id     = var.vpc_id
#   subnet_ids = var.private_subnet_ids
#
#   eks_managed_node_groups = {
#     default = {
#       min_size     = var.environment == "prd" ? 3 : 1
#       max_size     = var.environment == "prd" ? 10 : 3
#       desired_size = var.environment == "prd" ? 3 : 1
#
#       instance_types = ["t3.medium"]
#     }
#   }
#
#   tags = local.common_tags
# }

# =============================================================================
# RDS (Optional - uncomment to use)
# =============================================================================

# resource "aws_db_subnet_group" "main" {
#   name       = "${var.project}-${var.environment}"
#   subnet_ids = var.private_subnet_ids
#
#   tags = local.common_tags
# }

# resource "aws_db_instance" "main" {
#   identifier = "${var.project}-${var.environment}"
#
#   engine         = "postgres"
#   engine_version = "15"
#   instance_class = var.environment == "prd" ? "db.r6g.large" : "db.t3.micro"
#
#   allocated_storage     = 20
#   max_allocated_storage = 100
#   storage_encrypted     = true
#   kms_key_id           = var.kms_key_arn
#
#   db_subnet_group_name   = aws_db_subnet_group.main.name
#   vpc_security_group_ids = [aws_security_group.db.id]
#
#   multi_az               = var.environment == "prd" ? true : false
#   deletion_protection    = var.environment == "prd" ? true : false
#   skip_final_snapshot    = var.environment != "prd"
#   final_snapshot_identifier = var.environment == "prd" ? "${var.project}-${var.environment}-final" : null
#
#   tags = local.common_tags
#
#   lifecycle {
#     prevent_destroy = true
#   }
# }
