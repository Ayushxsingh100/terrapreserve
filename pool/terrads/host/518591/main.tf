terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

resource "aws_db_instance" "default" {
  identifier     = "rds-${var.workload}"
  db_name        = "pgdatabase"
  engine         = "postgres"
  engine_version = "15.3"
  username       = var.username
  password       = var.password
  multi_az       = false

  blue_green_update {
    enabled = false
  }

  db_subnet_group_name = aws_db_subnet_group.default.name
  publicly_accessible  = false

  instance_class        = var.instance_class
  allocated_storage     = 20
  max_allocated_storage = 30
  storage_type          = "gp3"
  ca_cert_identifier    = "rds-ca-rsa2048-g1"

  storage_encrypted      = true
  vpc_security_group_ids = [aws_security_group.postgresql.id]

  apply_immediately = true

  deletion_protection      = false
  skip_final_snapshot      = true
  delete_automated_backups = true
}

resource "aws_db_subnet_group" "default" {
  name       = "rds-subnets-${var.workload}"
  subnet_ids = var.subnets
}

resource "aws_security_group" "postgresql" {
  name        = "rds-${var.workload}-database"
  description = "Allow TLS inbound traffic to RDS PostgreSQL"
  vpc_id      = var.vpc_id

  tags = {
    Name = "sg-rds-${var.workload}"
  }
}

resource "aws_security_group_rule" "peering" {
  description       = "Allows peered connection"
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = [var.bastin_peering_cidr_block]
  security_group_id = aws_security_group.postgresql.id
}
