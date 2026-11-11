resource "aws_vpc" "net" {
  cidr_block           = "10.133.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.net.id
}

resource "aws_subnet" "pub" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.133.1.0/24"
  vpc_id            = aws_vpc.net.id
}

resource "aws_subnet" "pub_b" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.133.2.0/24"
  vpc_id            = aws_vpc.net.id
}

resource "aws_subnet" "priv_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.133.10.0/24"
  vpc_id            = aws_vpc.net.id
}

resource "aws_subnet" "priv_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.133.11.0/24"
  vpc_id            = aws_vpc.net.id
}

resource "aws_route_table" "pub_a" {
  vpc_id = aws_vpc.net.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
}

resource "aws_route_table_association" "ra_app" {
  route_table_id = aws_route_table.pub_a.id
  subnet_id      = aws_subnet.pub.id
}

resource "aws_route_table" "pub_b" {
  vpc_id = aws_vpc.net.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
}

resource "aws_route_table_association" "ra_app_b" {
  route_table_id = aws_route_table.pub_b.id
  subnet_id      = aws_subnet.pub_b.id
}

resource "aws_route_table" "priv_1" {
  vpc_id = aws_vpc.net.id
}

resource "aws_route_table_association" "ra_db_1" {
  route_table_id = aws_route_table.priv_1.id
  subnet_id      = aws_subnet.priv_1.id
}

resource "aws_route_table" "priv_2" {
  vpc_id = aws_vpc.net.id
}

resource "aws_route_table_association" "ra_db_2" {
  route_table_id = aws_route_table.priv_2.id
  subnet_id      = aws_subnet.priv_2.id
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

resource "aws_security_group" "web" {
  description = "Application security group for tpl-25"
  name        = "web-tpl-25"
  vpc_id      = aws_vpc.net.id

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "pg" {
  description = "Database security group for tpl-25"
  name        = "pg-tpl-25"
  vpc_id      = aws_vpc.net.id
}

resource "aws_security_group" "web_extra" {
  description = "Secondary application security group for tpl-25"
  name        = "web_extra-tpl-25"
  vpc_id      = aws_vpc.net.id
}

resource "aws_instance" "web" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.small"
  subnet_id              = aws_subnet.pub.id
  vpc_security_group_ids = [aws_security_group.web.id, aws_security_group.web_extra.id]
}

resource "aws_db_subnet_group" "pg" {
  name       = "pg-tpl-25"
  subnet_ids = [aws_subnet.priv_1.id, aws_subnet.priv_2.id]
}

resource "aws_db_instance" "pg" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.pg.name
  engine                 = "postgres"
  identifier             = "pg-tpl-25"
  instance_class         = "db.t3.micro"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.pg.id]
}
