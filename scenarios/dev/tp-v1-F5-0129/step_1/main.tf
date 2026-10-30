resource "aws_vpc" "corp_vpc" {
  cidr_block           = "10.103.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "corp_igw" {
  vpc_id = aws_vpc.corp_vpc.id
}

resource "aws_subnet" "frontend_subnet" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.103.1.0/24"
  vpc_id            = aws_vpc.corp_vpc.id
}

resource "aws_subnet" "backend_subnet_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.103.10.0/24"
  vpc_id            = aws_vpc.corp_vpc.id
}

resource "aws_subnet" "backend_subnet_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.103.11.0/24"
  vpc_id            = aws_vpc.corp_vpc.id
}

resource "aws_route_table" "frontend_rt" {
  vpc_id = aws_vpc.corp_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.corp_igw.id
  }
}

resource "aws_route_table_association" "assoc_app" {
  route_table_id = aws_route_table.frontend_rt.id
  subnet_id      = aws_subnet.frontend_subnet.id
}

resource "aws_security_group" "frontend_sg" {
  description = "Application security group for tpl-10"
  name        = "frontend_sg-tpl-10"
  vpc_id      = aws_vpc.corp_vpc.id

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "backend_sg" {
  description = "Database security group for tpl-10"
  name        = "backend_sg-tpl-10"
  vpc_id      = aws_vpc.corp_vpc.id

  ingress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.frontend_sg.id]
    to_port         = 5432
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "frontend_sg_extra" {
  description = "Secondary application security group for tpl-10"
  name        = "frontend_sg_extra-tpl-10"
  vpc_id      = aws_vpc.corp_vpc.id
}

resource "aws_instance" "frontend_server" {
  ami                    = "ami-0c55b159cbfafe1f0"
  count                  = 1
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.frontend_subnet.id
  vpc_security_group_ids = [aws_security_group.frontend_sg.id, aws_security_group.frontend_sg_extra.id]
}

resource "aws_db_subnet_group" "backend_sng" {
  name       = "backend_sng-tpl-10"
  subnet_ids = [aws_subnet.backend_subnet_1.id, aws_subnet.backend_subnet_2.id]
}

resource "aws_db_instance" "backend_database" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.backend_sng.name
  engine                 = "postgres"
  identifier             = "backend-database-tpl-10"
  instance_class         = "db.t3.nano"
  password               = var.db_password
  publicly_accessible    = true
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.backend_sg.id]
}
