resource "aws_vpc" "acme_vpc" {
  cidr_block           = "10.31.0.0/16"
  enable_dns_hostnames = false
  enable_dns_support   = true
}

resource "aws_internet_gateway" "acme_igw" {
  vpc_id = aws_vpc.acme_vpc.id
}

resource "aws_subnet" "acme_app_subnet" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.31.1.0/24"
  vpc_id            = aws_vpc.acme_vpc.id
}

resource "aws_subnet" "acme_db_subnet_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.31.10.0/24"
  vpc_id            = aws_vpc.acme_vpc.id
}

resource "aws_subnet" "acme_db_subnet_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.31.11.0/24"
  vpc_id            = aws_vpc.acme_vpc.id
}

resource "aws_route_table" "acme_public_rt" {
  vpc_id = aws_vpc.acme_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.acme_igw.id
  }
}

resource "aws_route_table_association" "acme_rta_app" {
  route_table_id = aws_route_table.acme_public_rt.id
  subnet_id      = aws_subnet.acme_app_subnet.id
}

resource "aws_security_group_rule" "acme_db_sg_from_app_5432" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.acme_db_sg.id
  source_security_group_id = aws_security_group.acme_app_sg.id
  to_port                  = 5432
  type                     = "ingress"
}

resource "aws_security_group_rule" "acme_db_sg_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.acme_db_sg.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group" "acme_app_sg" {
  description = "Application security group for tpl-29"
  name        = "acme_app_sg-tpl-29"
  vpc_id      = aws_vpc.acme_vpc.id

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 22
    protocol    = "tcp"
    to_port     = 22
  }

  egress {
    cidr_blocks = ["192.168.0.0/16"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "acme_db_sg" {
  description = "Database security group for tpl-29"
  name        = "acme_db_sg-tpl-29"
  vpc_id      = aws_vpc.acme_vpc.id
}

resource "aws_instance" "acme_app" {
  ami                    = local.app_ami
  instance_type          = "t3.large"
  subnet_id              = aws_subnet.acme_app_subnet.id
  vpc_security_group_ids = [aws_security_group.acme_app_sg.id]
}

resource "aws_db_subnet_group" "acme_db_sng" {
  name       = "acme_db_sng-tpl-29"
  subnet_ids = [aws_subnet.acme_db_subnet_1.id, aws_subnet.acme_db_subnet_2.id]
}

resource "aws_db_instance" "acme_db" {
  allocated_storage      = 40
  db_subnet_group_name   = aws_db_subnet_group.acme_db_sng.name
  engine                 = "postgres"
  identifier             = "acme-db-tpl-29"
  instance_class         = local.db_instance_class
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.acme_db_sg.id]
}
