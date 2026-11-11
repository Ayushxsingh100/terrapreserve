resource "aws_security_group_rule" "data_secgroup_from_app_5432" {
  cidr_blocks       = ["10.164.1.0/24"]
  from_port         = 5432
  protocol          = "tcp"
  security_group_id = aws_security_group.data_secgroup.id
  to_port           = 5432
  type              = "ingress"
}

resource "aws_security_group_rule" "data_secgroup_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.data_secgroup.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group" "data_secgroup" {
  description = "Database security group for tpl-19"
  name        = "data_secgroup-tpl-19"
  vpc_id      = aws_vpc.network.id
}

resource "aws_db_subnet_group" "data_subnets" {
  name       = "data_subnets-tpl-19"
  subnet_ids = [aws_subnet.data_tier_1.id, aws_subnet.data_tier_2.id, aws_subnet.data_tier_3.id]
}

resource "aws_db_instance" "data_instance" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.data_subnets.name
  engine                 = "postgres"
  identifier             = "data-instance-tpl-19"
  instance_class         = "db.t3.medium"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.data_secgroup.id]
}
