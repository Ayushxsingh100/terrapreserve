resource "aws_vpc" "corp_vpc" {
  cidr_block           = "10.123.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "corp_igw" {
  vpc_id = aws_vpc.corp_vpc.id
}

resource "aws_subnet" "frontend_subnet" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.123.1.0/24"
  vpc_id            = aws_vpc.corp_vpc.id
}

resource "aws_subnet" "backend_subnet" {
  count = 3

  availability_zone = ["us-east-1a", "us-east-1b", "us-east-1c"][count.index]
  cidr_block        = ["10.123.10.0/24", "10.123.11.0/24", "10.123.12.0/24"][count.index]
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

resource "aws_route_table" "backend_rt" {
  vpc_id = aws_vpc.corp_vpc.id
}

resource "aws_route_table_association" "assoc_db" {
  count = 3

  route_table_id = aws_route_table.backend_rt.id
  subnet_id      = aws_subnet.backend_subnet[count.index].id
}

resource "aws_security_group_rule" "backend_sg_from_app_5432" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.backend_sg.id
  source_security_group_id = aws_security_group.frontend_sg.id
  to_port                  = 5432
  type                     = "ingress"
}

resource "aws_security_group_rule" "backend_sg_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.backend_sg.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group" "frontend_sg" {
  description = "Application security group for tpl-21"
  name        = "frontend_sg-tpl-21"
  vpc_id      = aws_vpc.corp_vpc.id

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 22
    protocol    = "tcp"
    to_port     = 22
  }

  egress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_sg.id]
    to_port         = 5432
  }
}

resource "aws_security_group" "backend_sg" {
  description = "Database security group for tpl-21"
  name        = "backend_sg-tpl-21"
  vpc_id      = aws_vpc.corp_vpc.id
}

resource "aws_instance" "frontend_server" {
  ami                    = var.app_ami
  instance_type          = "t3.large"
  subnet_id              = aws_subnet.frontend_subnet.id
  vpc_security_group_ids = [aws_security_group.frontend_sg.id]
}

resource "aws_db_subnet_group" "backend_sng" {
  name       = "backend_sng-tpl-21"
  subnet_ids = [aws_subnet.backend_subnet[0].id, aws_subnet.backend_subnet[1].id, aws_subnet.backend_subnet[2].id]
}

resource "aws_db_instance" "backend_database" {
  allocated_storage      = 30
  db_subnet_group_name   = aws_db_subnet_group.backend_sng.name
  engine                 = "postgres"
  identifier             = "backend-database-tpl-21"
  instance_class         = var.db_instance_class
  password               = var.db_password
  port                   = 5433
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.backend_sg.id]
}
