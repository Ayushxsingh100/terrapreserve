resource "aws_security_group" "data_secgroup" {
  description = "Database security group for tpl-24"
  name        = "data_secgroup-tpl-24"
  vpc_id      = aws_vpc.network.id

  ingress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.web_secgroup.id]
    to_port         = 5432
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_db_subnet_group" "data_subnets" {
  name       = "data_subnets-tpl-24"
  subnet_ids = [aws_subnet.data_tier_1.id, aws_subnet.data_tier_2.id, aws_subnet.data_tier_3.id]
}

resource "aws_db_instance" "data_instance" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.data_subnets.name
  engine                 = "postgres"
  identifier             = "data-instance-tpl-24"
  instance_class         = "db.t3.small"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.data_secgroup.id]
}
