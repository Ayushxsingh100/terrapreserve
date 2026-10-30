resource "aws_vpc" "prod_vpc" {
  cidr_block           = "10.41.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "prod_igw" {
  vpc_id = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_app_subnet" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.41.1.0/24"
  vpc_id            = aws_vpc.prod_vpc.id
}

resource "aws_subnet" "prod_db_subnet" {
  count = 3

  availability_zone = ["us-east-1a", "us-east-1b", "us-east-1c"][count.index]
  cidr_block        = ["10.41.10.0/24", "10.41.11.0/24", "10.41.12.0/24"][count.index]
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

resource "aws_route_table" "prod_db_rt" {
  vpc_id = aws_vpc.prod_vpc.id
}

resource "aws_route_table_association" "prod_rta_db" {
  count = 3

  route_table_id = aws_route_table.prod_db_rt.id
  subnet_id      = aws_subnet.prod_db_subnet[count.index].id
}

resource "aws_security_group" "prod_app_sg" {
  description = "Application security group for tpl-06"
  name        = "prod_app_sg-tpl-06"
  vpc_id      = aws_vpc.prod_vpc.id

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "prod_db_sg" {
  description = "Database security group for tpl-06"
  name        = "prod_db_sg-tpl-06"
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
  ami                    = "ami-0d5eff06f840b45e9"
  instance_type          = "t3.medium"
  subnet_id              = aws_subnet.prod_app_subnet.id
  vpc_security_group_ids = [aws_security_group.prod_app_sg.id]
}

resource "aws_db_subnet_group" "prod_db_sng" {
  name       = "prod_db_sng-tpl-06"
  subnet_ids = [aws_subnet.prod_db_subnet[0].id, aws_subnet.prod_db_subnet[1].id, aws_subnet.prod_db_subnet[2].id]
}

resource "aws_db_instance" "prod_postgres_db" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.prod_db_sng.name
  engine                 = "postgres"
  identifier             = "prod-postgres-db-tpl-06"
  instance_class         = "db.t3.small"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.prod_db_sg.id]
}
