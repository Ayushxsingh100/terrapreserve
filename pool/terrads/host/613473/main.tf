resource "aws_db_subnet_group" "dagster" {
  name       = "${var.resource_prefix}-dagster-db-subnet-group"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "rds_sg" {
  name_prefix = "${var.resource_prefix}-rds-sg"
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]  # Adjust to your VPC CIDR
  }
}

resource "aws_db_instance" "dagster_postgres" {
  identifier             = "${var.resource_prefix}-dagster-db"
  engine                 = "postgres"
  engine_version         = "13"
  instance_class         = var.instance_class
  allocated_storage      = var.allocated_storage
  username               = "dagster"
  password               = var.db_password
  db_name                = "dagster"
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.dagster.name
  multi_az              = var.multi_az
  skip_final_snapshot   = false
  final_snapshot_identifier = "${var.resource_prefix}-dagster-final-snapshot"
}