locals {
  port = var.port != 0 ? var.port : (var.engine == "mysql" ? 3306 : var.engine == "mariadb" ? 3306 : var.engine == "oracle-se" ? 1521 : var.engine == "sqlserver-ex" ? 1433 : 5432)
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.project_name}-${var.environment}-db"
  subnet_ids = var.db_subnet_ids

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-db-subnets"
  })
}

resource "aws_security_group" "db" {
  name        = "${var.project_name}-${var.environment}-db"
  description = "Database access"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Application tier"
    from_port       = local.port
    to_port         = local.port
    protocol        = "tcp"
    security_groups = [var.app_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-db-sg"
  })
}

resource "aws_db_instance" "this" {
  identifier              = replace("${var.project_name}-${var.environment}-db", "_", "-")
  engine                  = var.engine
  engine_version          = var.engine_version
  instance_class          = var.instance_class
  allocated_storage       = var.allocated_storage
  max_allocated_storage   = var.max_allocated_storage
  username                = var.username
  password                = var.password
  db_subnet_group_name    = aws_db_subnet_group.this.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  skip_final_snapshot     = var.skip_final_snapshot
  deletion_protection     = var.deletion_protection
  multi_az                = var.multi_az
  backup_retention_period = var.backup_retention_period
  apply_immediately       = var.apply_immediately
  publicly_accessible     = var.publicly_accessible
  storage_encrypted       = var.storage_encrypted
  port                    = local.port

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-db"
  })
}
