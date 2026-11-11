resource "aws_security_group" "storage_access" {
  description = "Database security group for tpl-26"
  name        = "storage_access-tpl-26"
  vpc_id      = aws_vpc.platform.id

  ingress {
    from_port       = 5433
    protocol        = "tcp"
    security_groups = [aws_security_group.service_access.id]
    to_port         = 5433
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_db_subnet_group" "storage_subnets" {
  name       = "storage_subnets-tpl-26"
  subnet_ids = [aws_subnet.storage_1.id, aws_subnet.storage_2.id, aws_subnet.storage_3.id]
}

resource "aws_db_instance" "storage_db" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.storage_subnets.name
  engine                 = "postgres"
  identifier             = "storage-db-tpl-26"
  instance_class         = "db.t3.micro"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.storage_access.id]
}
