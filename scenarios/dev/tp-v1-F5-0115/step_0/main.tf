resource "aws_vpc" "main" {
  cidr_block           = "10.41.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "app" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.41.1.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "app_b" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.41.2.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.41.10.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.41.11.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_3" {
  availability_zone = "us-east-1c"
  cidr_block        = "10.41.12.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "rta_app" {
  route_table_id = aws_route_table.public.id
  subnet_id      = aws_subnet.app.id
}

resource "aws_route_table_association" "rta_app_b" {
  route_table_id = aws_route_table.public.id
  subnet_id      = aws_subnet.app_b.id
}

resource "aws_route_table" "db" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table_association" "rta_db_1" {
  route_table_id = aws_route_table.db.id
  subnet_id      = aws_subnet.db_1.id
}

resource "aws_route_table_association" "rta_db_2" {
  route_table_id = aws_route_table.db.id
  subnet_id      = aws_subnet.db_2.id
}

resource "aws_route_table_association" "rta_db_3" {
  route_table_id = aws_route_table.db.id
  subnet_id      = aws_subnet.db_3.id
}

resource "aws_security_group" "app" {
  description = "Application security group for tpl-28"
  name        = "app-tpl-28"
  vpc_id      = aws_vpc.main.id

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "db" {
  description = "Database security group for tpl-28"
  name        = "db-tpl-28"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
    to_port         = 5432
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "app_ops" {
  description = "Operations security group for tpl-28, attached to nothing"
  name        = "app_ops-tpl-28"
  vpc_id      = aws_vpc.main.id

  ingress {
    cidr_blocks = ["10.41.0.0/16"]
    from_port   = 443
    protocol    = "tcp"
    to_port     = 443
  }
}

resource "aws_instance" "app" {
  ami                    = local.app_ami
  instance_type          = local.app_instance_type
  subnet_id              = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.app.id]
}

resource "aws_db_subnet_group" "main" {
  name       = "main-tpl-28"
  subnet_ids = [aws_subnet.db_1.id, aws_subnet.db_2.id, aws_subnet.db_3.id]
}

resource "aws_db_instance" "main" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.main.name
  engine                 = "postgres"
  identifier             = "main-tpl-28"
  instance_class         = local.db_instance_class
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.db.id]
}
