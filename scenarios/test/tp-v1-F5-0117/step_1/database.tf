resource "aws_security_group" "prod_db_sg" {
  description = "Database security group for tpl-27"
  name        = "prod_db_sg-tpl-27"
  vpc_id      = aws_vpc.prod_vpc.id

  ingress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.prod_app_sg.id]
    to_port         = 5432
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_db_subnet_group" "prod_db_sng" {
  name       = "prod_db_sng-tpl-27"
  subnet_ids = [aws_subnet.prod_db_subnet_1.id, aws_subnet.prod_db_subnet_2.id]
}

resource "aws_db_instance" "prod_postgres_db" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.prod_db_sng.name
  engine                 = "postgres"
  identifier             = "prod-postgres-db-tpl-27"
  instance_class         = var.db_instance_class
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.prod_db_sg.id]
}
