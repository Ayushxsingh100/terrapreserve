resource "aws_security_group" "acme_db_sg" {
  description = "Database security group for tpl-14"
  name        = "acme_db_sg-tpl-14"
  vpc_id      = aws_vpc.acme_vpc.id

  ingress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.acme_app_sg.id]
    to_port         = 5432
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_db_subnet_group" "acme_db_sng" {
  name       = "acme_db_sng-tpl-14"
  subnet_ids = [aws_subnet.acme_db_subnet[0].id, aws_subnet.acme_db_subnet[1].id]
}

resource "aws_db_instance" "acme_db" {
  allocated_storage      = 30
  db_subnet_group_name   = aws_db_subnet_group.acme_db_sng.name
  engine                 = "postgres"
  identifier             = "acme-db-tpl-14"
  instance_class         = "db.t3.small"
  password               = var.db_password
  port                   = 5433
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.acme_db_sg.id]
}
