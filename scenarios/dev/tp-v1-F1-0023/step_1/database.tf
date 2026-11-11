resource "aws_security_group_rule" "prod_db_sg_from_app_5432" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.prod_db_sg.id
  source_security_group_id = aws_security_group.prod_app_sg.id
  to_port                  = 5432
  type                     = "ingress"
}

resource "aws_security_group_rule" "prod_db_sg_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.prod_db_sg.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group" "prod_db_sg" {
  description = "Database security group for tpl-33"
  name        = "prod_db_sg-tpl-33"
  vpc_id      = aws_vpc.prod_vpc.id
}

resource "aws_db_subnet_group" "prod_db_sng" {
  name       = "prod_db_sng-tpl-33"
  subnet_ids = [aws_subnet.prod_db_subnet[0].id, aws_subnet.prod_db_subnet[1].id]
}

resource "aws_db_instance" "prod_postgres_db" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.prod_db_sng.name
  engine                 = "postgres"
  identifier             = "prod-postgres-db-tpl-33"
  instance_class         = local.db_instance_class
  password               = var.db_password
  publicly_accessible    = true
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.prod_db_sg.id]
}
