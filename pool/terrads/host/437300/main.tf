resource "aws_db_instance" "default" {
  identifier = "pg-${var.project_name}-database-1"

  db_name        = var.db_name
  engine         = "postgres"
  engine_version = var.engine_version

  username = var.username
  password = var.password

  iam_database_authentication_enabled = false

  availability_zone = var.availability_zone

  publicly_accessible = var.publicly_accessible
  instance_class      = var.instance_class
  port                = 5432
  allocated_storage   = 20
  storage_type        = "gp3"
  storage_encrypted   = true
  multi_az            = false

  ca_cert_identifier = var.ca_cert_identifier

  allow_major_version_upgrade = false
  auto_minor_version_upgrade  = true
  apply_immediately           = false

  deletion_protection      = false
  skip_final_snapshot      = true
  delete_automated_backups = true

  performance_insights_enabled = false

  db_subnet_group_name   = aws_db_subnet_group.default.name
  vpc_security_group_ids = [aws_security_group.main.id]

  blue_green_update {
    enabled = false
  }
}

resource "aws_db_subnet_group" "default" {
  name       = "rds-group-${var.project_name}"
  subnet_ids = var.subnets_ids
}

resource "aws_security_group" "main" {
  name        = "${var.project_name}-databases"
  description = "Allow Traffic"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.project_name}-databases"
  }
}

resource "aws_security_group_rule" "postgresql" {
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = [var.vpc_cidr_block]
  security_group_id = aws_security_group.main.id
}

resource "aws_security_group_rule" "vpc_glue_self_reference" {
  description              = "Self reference to allow Glue connections"
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  security_group_id        = aws_security_group.main.id
  source_security_group_id = aws_security_group.main.id
}
