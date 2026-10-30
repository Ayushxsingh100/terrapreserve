resource "aws_security_group" "rds_sg" {
  name        = "rds-security-group"
  description = "Security group for RDS database"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL access from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  ingress {
    description     = "PostgreSQL from EKS to RDS security group"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_to_rds_sg.id]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "rds-security-group"
  }
}

resource "aws_security_group" "eks_to_rds_sg" {
  name        = "eks-to-rds-security-group"
  description = "Security group for EKS nodes to access RDS"
  vpc_id      = var.vpc_id

  egress {
    description = "PostgreSQL access to RDS"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "eks-to-rds-security-group"
  }
}
