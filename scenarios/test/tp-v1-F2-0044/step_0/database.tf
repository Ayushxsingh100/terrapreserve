resource "aws_security_group_rule" "db_public_5432" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 5432
  protocol          = "tcp"
  security_group_id = aws_security_group.db.id
  to_port           = 5432
  type              = "ingress"
}

resource "aws_security_group_rule" "db_from_app_5432" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = aws_security_group.app.id
  to_port                  = 5432
  type                     = "ingress"
}

resource "aws_security_group_rule" "db_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.db.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group" "db" {
  description = "Database security group for tpl-17"
  name        = "db-tpl-17"
  vpc_id      = aws_vpc.main.id
}

resource "aws_db_subnet_group" "main" {
  name       = "main-tpl-17"
  subnet_ids = [aws_subnet.db_1.id, aws_subnet.db_2.id, aws_subnet.db_3.id]
}

resource "aws_db_instance" "main" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.main.name
  engine                 = "postgres"
  identifier             = "main-tpl-17"
  instance_class         = var.db_instance_class
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.db.id]
}
