#=============================================================================
# Security Module - Security Groups
# Secure Cloud Computing - Portfolio 2
#
# Defense-in-Depth Approach:
# - Each team has dedicated security group
# - Least privilege inbound/outbound rules
# - ALB-only access for web instances
#=============================================================================

#-----------------------------------------------------------------------------
# ALB Security Group
#-----------------------------------------------------------------------------

resource "aws_security_group" "alb" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = var.vpc_id

  # Inbound HTTP from internet
  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Inbound HTTPS from internet
  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound to VPC only (to instances)
  egress {
    description = "All traffic to VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-alb-sg"
    Team = "Infrastructure"
  }
}

#-----------------------------------------------------------------------------
# SalesTeam Security Group (Public Subnet)
# Requirements: ReadOnly access, Internet via IGW
#-----------------------------------------------------------------------------

resource "aws_security_group" "sales" {
  name        = "${var.project_name}-${var.environment}-sales-sg"
  description = "Security group for SalesTeam - Public subnet with ALB access"
  vpc_id      = var.vpc_id

  # Inbound HTTP from ALB only (not directly from internet)
  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Inbound SSH from admin IPs only
  ingress {
    description = "SSH from admin IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  # Outbound HTTPS (for AWS APIs)
  egress {
    description = "HTTPS outbound"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound HTTP
  egress {
    description = "HTTP outbound"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound DNS
  egress {
    description = "DNS outbound"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-sales-sg"
    Team = "SalesTeam"
  }
}

#-----------------------------------------------------------------------------
# ComplianceTeam Security Group (Private Subnet - Isolated)
# Requirements: Audit access, NAT-only outbound, No direct internet
#-----------------------------------------------------------------------------

resource "aws_security_group" "compliance" {
  name        = "${var.project_name}-${var.environment}-compliance-sg"
  description = "Security group for ComplianceTeam - Private subnet, isolated"
  vpc_id      = var.vpc_id

  # Inbound from VPC only (no internet access)
  ingress {
    description = "All traffic from VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  # Outbound HTTPS via NAT (for AWS APIs and audit logs)
  egress {
    description = "HTTPS via NAT Gateway"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound DNS
  egress {
    description = "DNS outbound"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound to VPC (internal communication)
  egress {
    description = "All traffic to VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-compliance-sg"
    Team = "ComplianceTeam"
  }
}

#-----------------------------------------------------------------------------
# DTransformationTeam Security Group (Public Subnet)
# Requirements: Read/Write to S3, Data processing
#-----------------------------------------------------------------------------

resource "aws_security_group" "dtransformation" {
  name        = "${var.project_name}-${var.environment}-dtransformation-sg"
  description = "Security group for Digital Transformation Team"
  vpc_id      = var.vpc_id

  # Inbound from VPC
  ingress {
    description = "All traffic from VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  # Inbound SSH from admin IPs
  ingress {
    description = "SSH from admin IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  # Outbound HTTPS (for AWS APIs - S3, etc.)
  egress {
    description = "HTTPS for AWS APIs"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound to VPC
  egress {
    description = "All traffic to VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-dtransformation-sg"
    Team = "DTransformationTeam"
  }
}

#-----------------------------------------------------------------------------
# DevOpsTeam Security Group (Public Subnet)
# Requirements: EC2, ASG, ALB management
#-----------------------------------------------------------------------------

resource "aws_security_group" "devops" {
  name        = "${var.project_name}-${var.environment}-devops-sg"
  description = "Security group for DevOps Team - Infrastructure management"
  vpc_id      = var.vpc_id

  # Inbound SSH from admin IPs
  ingress {
    description = "SSH from admin IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  # Inbound custom ports for CI/CD tools
  ingress {
    description = "CI/CD ports"
    from_port   = 8080
    to_port     = 8090
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  # Inbound from VPC
  ingress {
    description = "All traffic from VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  # Outbound all (for deployments and management)
  egress {
    description = "All outbound for deployments"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-devops-sg"
    Team = "DevOpsTeam"
  }
}

#-----------------------------------------------------------------------------
# RedTeam Security Group (Public Subnet)
# Requirements: Security testing, read-only security config access
#-----------------------------------------------------------------------------

resource "aws_security_group" "redteam" {
  name        = "${var.project_name}-${var.environment}-redteam-sg"
  description = "Security group for Red Team - Security testing"
  vpc_id      = var.vpc_id

  # Inbound SSH from security team IPs
  ingress {
    description = "SSH from security team"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  # Inbound from VPC
  ingress {
    description = "All traffic from VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  # Outbound all (for security scanning)
  egress {
    description = "All outbound for security scanning"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redteam-sg"
    Team = "RedTeam"
  }
}

#-----------------------------------------------------------------------------
# AdministrativeTeam Security Group (Public Subnet)
# Requirements: IAM and billing access, MFA required
#-----------------------------------------------------------------------------

resource "aws_security_group" "administrative" {
  name        = "${var.project_name}-${var.environment}-administrative-sg"
  description = "Security group for Administrative Team"
  vpc_id      = var.vpc_id

  # Inbound SSH from admin IPs
  ingress {
    description = "SSH from admin IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  # Inbound RDP from admin IPs (Windows if needed)
  ingress {
    description = "RDP from admin IPs"
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  # Inbound from VPC
  ingress {
    description = "All traffic from VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  # Outbound all
  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-administrative-sg"
    Team = "AdministrativeTeam"
  }
}
