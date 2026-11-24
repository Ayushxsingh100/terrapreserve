resource "aws_vpc" "acme_vpc" {
  cidr_block           = "10.66.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "acme_igw" {
  vpc_id = aws_vpc.acme_vpc.id
}

resource "aws_subnet" "acme_app_subnet" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.66.1.0/24"
  vpc_id            = aws_vpc.acme_vpc.id
}

resource "aws_subnet" "acme_app_subnet_b" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.66.2.0/24"
  vpc_id            = aws_vpc.acme_vpc.id
}

resource "aws_subnet" "acme_db_subnet_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.66.10.0/24"
  vpc_id            = aws_vpc.acme_vpc.id
}

resource "aws_subnet" "acme_db_subnet_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.66.11.0/24"
  vpc_id            = aws_vpc.acme_vpc.id
}

resource "aws_subnet" "acme_app_subnet_spare" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.66.200.0/24"
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

resource "aws_route_table_association" "acme_rta_app_b" {
  route_table_id = aws_route_table.acme_public_rt.id
  subnet_id      = aws_subnet.acme_app_subnet_b.id
}

resource "aws_security_group" "acme_app_sg" {
  description = "Application security group for tpl-20"
  name        = "acme_app_sg-tpl-20"
  vpc_id      = aws_vpc.acme_vpc.id

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "acme_db_sg" {
  description = "Database security group for tpl-20"
  name        = "acme_db_sg-tpl-20"
  vpc_id      = aws_vpc.acme_vpc.id

  ingress {
    cidr_blocks = ["10.0.0.0/8"]
    from_port   = 5432
    protocol    = "tcp"
    to_port     = 5432
  }

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

resource "aws_instance" "acme_app" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.acme_app_subnet.id
  vpc_security_group_ids = [aws_security_group.acme_app_sg.id]
}

resource "aws_db_subnet_group" "acme_db_sng" {
  name       = "acme_db_sng-tpl-20"
  subnet_ids = [aws_subnet.acme_db_subnet_1.id, aws_subnet.acme_db_subnet_2.id]
}

resource "aws_db_instance" "acme_db" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.acme_db_sng.name
  engine                 = "postgres"
  identifier             = "acme-db-tpl-20"
  instance_class         = "db.t3.micro"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.acme_db_sg.id]
}
