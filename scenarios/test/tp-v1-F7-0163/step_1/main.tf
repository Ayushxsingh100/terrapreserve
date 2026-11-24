resource "aws_vpc" "platform" {
  cidr_block           = "10.106.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "edge" {
  vpc_id = aws_vpc.platform.id
}

resource "aws_subnet" "service" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.106.1.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_subnet" "service_b" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.106.2.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_subnet" "storage_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.106.10.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_subnet" "storage_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.106.11.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_subnet" "service_spare" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.106.200.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_route_table" "edge_routes" {
  vpc_id = aws_vpc.platform.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.edge.id
  }
}

resource "aws_route_table_association" "route_link_app" {
  route_table_id = aws_route_table.edge_routes.id
  subnet_id      = aws_subnet.service.id
}

resource "aws_route_table_association" "route_link_app_b" {
  route_table_id = aws_route_table.edge_routes.id
  subnet_id      = aws_subnet.service_b.id
}

resource "aws_security_group_rule" "storage_access_from_app_5432" {
  cidr_blocks       = ["10.106.1.0/24"]
  from_port         = 5432
  protocol          = "tcp"
  security_group_id = aws_security_group.storage_access.id
  to_port           = 5432
  type              = "ingress"
}

resource "aws_security_group_rule" "storage_access_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.storage_access.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group" "service_access" {
  description = "Application security group for tpl-13"
  name        = "service_access-tpl-13"
  vpc_id      = aws_vpc.platform.id

  egress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.storage_access.id]
    to_port         = 5432
  }
}

resource "aws_security_group" "storage_access" {
  description = "Database security group for tpl-13"
  name        = "storage_access-tpl-13"
  vpc_id      = aws_vpc.platform.id
}

resource "aws_instance" "service_node" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.nano"
  subnet_id              = aws_subnet.service.id
  vpc_security_group_ids = [aws_security_group.service_access.id]
}

resource "aws_db_subnet_group" "storage_subnets" {
  name       = "storage_subnets-tpl-13"
  subnet_ids = [aws_subnet.storage_1.id, aws_subnet.storage_2.id]
}

resource "aws_db_instance" "storage_db" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.storage_subnets.name
  engine                 = "postgres"
  identifier             = "storage-db-tpl-13"
  instance_class         = "db.t3.micro"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.storage_access.id]
}
