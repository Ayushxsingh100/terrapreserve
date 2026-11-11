resource "aws_vpc" "net" {
  cidr_block           = "10.169.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.net.id
}

resource "aws_subnet" "pub" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.169.1.0/24"
  vpc_id            = aws_vpc.net.id
}

resource "aws_subnet" "priv" {
  count = 3

  availability_zone = ["us-east-1a", "us-east-1b", "us-east-1c"][count.index]
  cidr_block        = ["10.169.10.0/24", "10.169.11.0/24", "10.169.12.0/24"][count.index]
  vpc_id            = aws_vpc.net.id
}

resource "aws_subnet" "pub_spare" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.169.200.0/24"
  vpc_id            = aws_vpc.net.id
}

resource "aws_route_table" "pub" {
  vpc_id = aws_vpc.net.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
}

resource "aws_route_table_association" "ra_app" {
  route_table_id = aws_route_table.pub.id
  subnet_id      = aws_subnet.pub.id
}

resource "aws_route_table" "priv" {
  vpc_id = aws_vpc.net.id
}

resource "aws_route_table_association" "ra_db" {
  count = 3

  route_table_id = aws_route_table.priv.id
  subnet_id      = aws_subnet.priv[count.index].id
}

resource "aws_security_group_rule" "pg_from_app_5432" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.pg.id
  source_security_group_id = aws_security_group.web.id
  to_port                  = 5432
  type                     = "ingress"
}

resource "aws_security_group_rule" "pg_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.pg.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group_rule" "web_egress_db" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.web.id
  source_security_group_id = aws_security_group.pg.id
  to_port                  = 5432
  type                     = "egress"
}

resource "aws_security_group" "web" {
  description = "Application security group for tpl-15"
  name        = "web-tpl-15"
  vpc_id      = aws_vpc.net.id
}

resource "aws_security_group" "pg" {
  description = "Database security group for tpl-15"
  name        = "pg-tpl-15"
  vpc_id      = aws_vpc.net.id
}

resource "aws_instance" "web" {
  ami                    = local.app_ami
  instance_type          = local.app_instance_type
  subnet_id              = aws_subnet.pub.id
  vpc_security_group_ids = [aws_security_group.web.id]
}

resource "aws_db_subnet_group" "pg" {
  name       = "pg-tpl-15"
  subnet_ids = [aws_subnet.priv[0].id, aws_subnet.priv[1].id, aws_subnet.priv[2].id]
}

resource "aws_db_instance" "pg" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.pg.name
  engine                 = "postgres"
  identifier             = "pg-tpl-15"
  instance_class         = local.db_instance_class
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.pg.id]
}
