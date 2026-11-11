resource "aws_security_group" "db" {
  description = "Database security group for tpl-08"
  name        = "db-tpl-08"
  vpc_id      = aws_vpc.main.id

  ingress {
    cidr_blocks      = ["10.0.0.0/8"]
    from_port        = 5432
    ipv6_cidr_blocks = ["::/0"]
    protocol         = "tcp"
    to_port          = 5432
  }

  ingress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
    to_port         = 5432
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "main-tpl-08"
  subnet_ids = [aws_subnet.db_1.id, aws_subnet.db_2.id, aws_subnet.db_3.id]
}

resource "aws_db_instance" "main" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.main.name
  engine                 = "postgres"
  identifier             = "main-tpl-08"
  instance_class         = "db.t3.micro"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.db.id]
}
