resource "aws_vpc" "main" {
  cidr_block           = "10.104.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "app" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.104.1.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.104.10.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.104.11.0/24"
  vpc_id            = aws_vpc.main.id
}

resource "aws_subnet" "db_3" {
  availability_zone = "us-east-1c"
  cidr_block        = "10.104.12.0/24"
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

resource "aws_security_group_rule" "app_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.app.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group" "app" {
  description = "Application security group for tpl-08"
  name        = "app-tpl-08"
  vpc_id      = aws_vpc.main.id
}

resource "aws_security_group" "db" {
  description = "Database security group for tpl-08"
  name        = "db-tpl-08"
  vpc_id      = aws_vpc.main.id

  ingress {
    cidr_blocks = ["10.0.0.0/8"]
    from_port   = 5432
    protocol    = "tcp"
    to_port     = 5432
  }

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

resource "aws_instance" "app" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.nano"
  subnet_id              = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.app.id]
}

resource "aws_db_subnet_group" "main" {
  name       = "main-tpl-08"
  subnet_ids = [aws_subnet.db_1.id, aws_subnet.db_2.id, aws_subnet.db_3.id]
}

resource "aws_db_instance" "main" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.main.name
  engine                 = "postgres"
  identifier             = "main-tpl-08"
  instance_class         = "db.t3.micro"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.db.id]
}

resource "aws_security_group_rule" "app_ingress_ssh" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 22
  protocol          = "tcp"
  security_group_id = aws_security_group.app.id
  to_port           = 22
  type              = "ingress"
}
