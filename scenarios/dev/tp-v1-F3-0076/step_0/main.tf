resource "aws_vpc" "vpc_main" {
  cidr_block           = "10.124.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "igw_main" {
  vpc_id = aws_vpc.vpc_main.id
}

resource "aws_subnet" "sub_app" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.124.1.0/24"
  vpc_id            = aws_vpc.vpc_main.id
}

resource "aws_subnet" "sub_db_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.124.10.0/24"
  vpc_id            = aws_vpc.vpc_main.id
}

resource "aws_subnet" "sub_db_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.124.11.0/24"
  vpc_id            = aws_vpc.vpc_main.id
}

resource "aws_route_table" "rt_public" {
  vpc_id = aws_vpc.vpc_main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw_main.id
  }
}

resource "aws_route_table_association" "rta_app" {
  route_table_id = aws_route_table.rt_public.id
  subnet_id      = aws_subnet.sub_app.id
}

resource "aws_route_table" "rt_db" {
  vpc_id = aws_vpc.vpc_main.id
}

resource "aws_route_table_association" "rta_db_1" {
  route_table_id = aws_route_table.rt_db.id
  subnet_id      = aws_subnet.sub_db_1.id
}

resource "aws_route_table_association" "rta_db_2" {
  route_table_id = aws_route_table.rt_db.id
  subnet_id      = aws_subnet.sub_db_2.id
}

resource "aws_security_group" "sg_app" {
  description = "Application security group for tpl-02"
  name        = "sg_app-tpl-02"
  vpc_id      = aws_vpc.vpc_main.id

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "sg_db" {
  description = "Database security group for tpl-02"
  name        = "sg_db-tpl-02"
  vpc_id      = aws_vpc.vpc_main.id

  ingress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_app.id]
    to_port         = 5432
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_instance" "ec2_app" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.small"
  subnet_id              = aws_subnet.sub_app.id
  vpc_security_group_ids = [aws_security_group.sg_app.id]
}

resource "aws_db_subnet_group" "dbsng_main" {
  name       = "dbsng_main-tpl-02"
  subnet_ids = [aws_subnet.sub_db_1.id, aws_subnet.sub_db_2.id]
}

resource "aws_db_instance" "rds_postgres" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.dbsng_main.name
  engine                 = "postgres"
  identifier             = "rds-postgres-tpl-02"
  instance_class         = "db.t3.small"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.sg_db.id]
}
