# Security Group for RDS
resource "aws_security_group" "rds_sg" {
  name        = "cloudnorth-rds-sg"
  description = "Security group for RDS database"
  vpc_id      = var.vpc_id

  ingress {
    description     = "MySQL"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = var.ec2_security_group_ids
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "cloudnorth-rds-sg"
  }
}

# RDS Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "cloudnorth-rds-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "cloudnorth-rds-subnet-group"
  }
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier             = "cloudnorth-db"
  engine                 = "mysql"
  engine_version         = var.engine_version  # Use variable
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  storage_type           = "gp2"
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  parameter_group_name   = "default.mysql8.0"
  skip_final_snapshot    = true
  publicly_accessible    = false
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  tags = {
    Name = "cloudnorth-rds"
  }
}
