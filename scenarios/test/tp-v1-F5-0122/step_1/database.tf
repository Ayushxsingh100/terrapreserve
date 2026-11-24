resource "aws_security_group" "pg" {
  description = "Database security group for tpl-12"
  name        = "pg-tpl-12-v2"
  vpc_id      = aws_vpc.net.id

  ingress {
    from_port       = 5433
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
    to_port         = 5433
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_db_subnet_group" "pg" {
  name       = "pg-tpl-12"
  subnet_ids = [aws_subnet.priv_1.id, aws_subnet.priv_2.id, aws_subnet.priv_3.id]
}

resource "aws_db_instance" "pg" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.pg.name
  engine                 = "postgres"
  identifier             = "pg-tpl-12"
  instance_class         = local.db_instance_class
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.pg.id]
}
