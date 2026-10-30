resource "aws_db_subnet_group" "this" {
  name       = "${var.project_name}-db-subnets"
  subnet_ids = var.private_db_subnet_ids
  tags       = merge(var.tags, { Name = "${var.project_name}-db-subnets" })
}

resource "aws_security_group" "db" {
  name_prefix = "${var.project_name}-db-sg"
  description = "Database security group for ${var.project_name}"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = var.db_port
    to_port     = var.db_port
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  dynamic "ingress" {
    for_each = var.app_security_group_id == null ? [] : [var.app_security_group_id]
    content {
      from_port       = var.db_port
      to_port         = var.db_port
      protocol        = "tcp"
      security_groups = [ingress.value]
    }
  }

  dynamic "ingress" {
    for_each = var.admin_cidr == null ? [] : [var.admin_cidr]
    content {
      from_port   = var.db_port
      to_port     = var.db_port
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project_name}-db-sg" })
}

resource "aws_db_instance" "this" {
  identifier              = "${var.project_name}-db"
  engine                  = var.db_engine
  engine_version          = var.db_engine_version
  instance_class          = var.db_instance_class
  db_name                 = var.db_name
  username                = var.db_username
  password                = var.db_password
  allocated_storage       = var.db_allocated_storage
  storage_type            = "gp3"
  multi_az                = false
  publicly_accessible     = false
  vpc_security_group_ids  = [aws_security_group.db.id]
  db_subnet_group_name    = aws_db_subnet_group.this.name
  backup_retention_period = 7
  deletion_protection     = false
  skip_final_snapshot     = true
  tags                    = merge(var.tags, { Name = "${var.project_name}-db" })
}
