resource "aws_vpc" "prod_vpc" {
  cidr_block           = "10.93.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "prod_igw" {
  vpc_id = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_app_subnet" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.93.1.0/24"
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_db_subnet_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.93.10.0/24"
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_db_subnet_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.93.11.0/24"
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_app_subnet_spare" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.93.200.0/24"
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_route_table" "prod_public_rt" {
  vpc_id = aws_vpc.prod_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.prod_igw.id
  }
}

resource "aws_route_table_association" "prod_rta_app" {
  route_table_id = aws_route_table.prod_public_rt.id
  subnet_id      = aws_subnet.prod_app_subnet.id
}

resource "aws_security_group_rule" "prod_app_sg_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 443
  protocol          = "tcp"
  security_group_id = aws_security_group.prod_app_sg.id
  to_port           = 443
  type              = "egress"
}

resource "aws_security_group" "prod_app_sg" {
  description = "Application security group for tpl-22"
  name        = "prod_app_sg-tpl-22"
  vpc_id      = aws_vpc.prod_vpc.id
}

resource "aws_security_group" "prod_db_sg" {
  description = "Database security group for tpl-22"
  name        = "prod_db_sg-tpl-22"
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

resource "aws_instance" "prod_app_server" {
  ami                    = var.app_ami
  instance_type          = var.app_instance_type
  subnet_id              = aws_subnet.prod_app_subnet.id
  vpc_security_group_ids = [aws_security_group.prod_app_sg.id]
}

resource "aws_db_subnet_group" "prod_db_sng" {
  name       = "prod_db_sng-tpl-22"
  subnet_ids = [aws_subnet.prod_db_subnet_1.id, aws_subnet.prod_db_subnet_2.id]
}

resource "aws_db_instance" "prod_postgres_db" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.prod_db_sng.name
  engine                 = "postgres"
  identifier             = "prod-postgres-db-tpl-22"
  instance_class         = var.db_instance_class
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.prod_db_sg.id]
}
