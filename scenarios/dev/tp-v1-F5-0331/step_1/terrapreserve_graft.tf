resource "aws_vpc" "tp_vpc" {
  cidr_block           = "172.25.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "tp_igw" {
  vpc_id = aws_vpc.tp_vpc.id
}

resource "aws_subnet" "tp_app_subnet" {
  availability_zone = "us-east-1a"
  cidr_block        = "172.25.1.0/24"
  vpc_id            = aws_vpc.tp_vpc.id
}

resource "aws_subnet" "tp_db_subnet_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "172.25.10.0/24"
  vpc_id            = aws_vpc.tp_vpc.id
}

resource "aws_subnet" "tp_db_subnet_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "172.25.11.0/24"
  vpc_id            = aws_vpc.tp_vpc.id
}

resource "aws_route_table" "tp_public_rt" {
  vpc_id = aws_vpc.tp_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.tp_igw.id
  }
}

resource "aws_route_table_association" "tp_rta_app" {
  route_table_id = aws_route_table.tp_public_rt.id
  subnet_id      = aws_subnet.tp_app_subnet.id
}

resource "aws_security_group" "tp_app_sg" {
  description = "TerraPreserve app security group"
  name        = "tp-app-sg"
  vpc_id      = aws_vpc.tp_vpc.id
}

resource "aws_security_group" "tp_db_sg" {
  description = "TerraPreserve database security group"
  name        = "tp-db-sg"
  vpc_id      = aws_vpc.tp_vpc.id
}

resource "aws_security_group_rule" "tp_app_ingress_ssh" {
  cidr_blocks       = ["10.0.0.0/8"]
  from_port         = 22
  protocol          = "tcp"
  security_group_id = aws_security_group.tp_app_sg.id
  to_port           = 22
  type              = "ingress"
}

resource "aws_security_group_rule" "tp_app_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.tp_app_sg.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group_rule" "tp_db_ingress_postgres" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.tp_db_sg.id
  source_security_group_id = aws_security_group.tp_app_sg.id
  to_port                  = 5432
  type                     = "ingress"
}

resource "aws_instance" "tp_app" {
  ami                    = "ami-0c55b159cbfafe1f0"
  count                  = 1
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.tp_app_subnet.id
  vpc_security_group_ids = [aws_security_group.tp_app_sg.id]
}

resource "aws_db_subnet_group" "tp_db_subnet_group" {
  name       = "tp-db-subnet-group"
  subnet_ids = [aws_subnet.tp_db_subnet_1.id, aws_subnet.tp_db_subnet_2.id]
}

resource "aws_db_instance" "tp_db" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.tp_db_subnet_group.name
  engine                 = "postgres"
  identifier             = "tp-db-instance"
  instance_class         = "db.t3.micro"
  password               = var.tp_db_password
  publicly_accessible    = true
  skip_final_snapshot    = true
  username               = "tp_admin"
  vpc_security_group_ids = [aws_security_group.tp_db_sg.id]
}
