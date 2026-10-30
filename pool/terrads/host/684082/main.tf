terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-pg-subnets"
  subnet_ids = var.private_subnet_ids
}

resource "aws_security_group" "pg" {
  name   = "${var.name}-pg-sg"
  vpc_id = var.vpc_id
}

resource "aws_security_group_rule" "from_eks" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.pg.id
  source_security_group_id = var.eks_security_group_id
}

resource "aws_security_group_rule" "egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.pg.id
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_db_instance" "this" {
  identifier = "${var.name}-postgres"

  engine               = "postgres"
  engine_version       = "15"
  instance_class       = var.instance_class
  allocated_storage    = var.allocated_storage

  db_subnet_group_name = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.pg.id]

  username = var.username
  password = var.password

  multi_az            = var.multi_az
  publicly_accessible = false
  skip_final_snapshot = true

  backup_retention_period = 7
}
