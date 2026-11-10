# RDS MariaDB database module


# Get default VPC

# Get subnets for DB subnet group

# DB subnet group
resource "aws_db_subnet_group" "this" {
  name       = "${var.environment}-db-subnet-group"
  subnet_ids = var.tp_ds_aws_subnets_available.ids

  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-db-subnet-group"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Security group for RDS
resource "aws_security_group" "db_sg" {
  name_prefix = "${var.environment}-db-sg-"
  description = "Security group for ${var.environment} RDS database"
  vpc_id      = var.tp_ds_aws_vpc_default.id

  ingress {
    description = "MariaDB from VPC"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [var.tp_ds_aws_vpc_default.cidr_block]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-db-sg"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# RDS MariaDB instance
resource "aws_db_instance" "this" {
  identifier = "${var.environment}-${var.db_name}"

  # Engine configuration
  engine               = var.db_engine
  engine_version       = var.db_engine_version
  instance_class       = var.db_instance_class
  allocated_storage    = var.db_allocated_storage
  storage_type         = "gp2"
  storage_encrypted    = true

  # Database configuration
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password      # For demo only. Use AWS Secrets Manager in production
  port     = 3306

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  publicly_accessible    = false

  # Free tier optimizations :):
  multi_az                 = false
  backup_retention_period  = 0
  skip_final_snapshot      = true

  tags = merge(
    var.common_tags,
    {
      Name        = "${var.environment}-${var.db_name}"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  lifecycle {
    ignore_changes = [password]
  }
}
