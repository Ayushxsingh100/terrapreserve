resource "aws_vpc" "platform" {
  cidr_block           = "10.35.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "edge" {
  vpc_id = aws_vpc.platform.id
}

resource "aws_subnet" "service" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.35.1.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_subnet" "storage" {
  count = 2

  availability_zone = ["us-east-1a", "us-east-1b"][count.index]
  cidr_block        = ["10.35.10.0/24", "10.35.11.0/24"][count.index]
  vpc_id            = aws_vpc.platform.id
}

resource "aws_route_table" "edge_routes_a" {
  vpc_id = aws_vpc.platform.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.edge.id
  }
}

resource "aws_route_table_association" "route_link_app" {
  route_table_id = aws_route_table.edge_routes_a.id
  subnet_id      = aws_subnet.service.id
}

resource "aws_route_table" "storage_routes" {
  count = 2

  vpc_id = aws_vpc.platform.id
}

resource "aws_route_table_association" "route_link_db" {
  count = 2

  route_table_id = aws_route_table.storage_routes[count.index].id
  subnet_id      = aws_subnet.storage[count.index].id
}

resource "aws_security_group" "service_access" {
  description = "Application security group for tpl-16"
  name        = "service_access-tpl-16"
  vpc_id      = aws_vpc.platform.id

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "storage_access" {
  description = "Database security group for tpl-16"
  name        = "storage_access-tpl-16-v2"
  vpc_id      = aws_vpc.platform.id

  ingress {
    from_port       = 5433
    protocol        = "tcp"
    security_groups = [aws_security_group.service_access.id]
    to_port         = 5433
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "service_access_extra" {
  description = "Secondary application security group for tpl-16"
  name        = "service_access_extra-tpl-16"
  vpc_id      = aws_vpc.platform.id
}

resource "aws_instance" "service_node" {
  ami                    = var.app_ami
  instance_type          = var.app_instance_type
  subnet_id              = aws_subnet.service.id
  vpc_security_group_ids = [aws_security_group.service_access.id, aws_security_group.service_access_extra.id]
}

resource "aws_db_subnet_group" "storage_subnets" {
  name       = "storage_subnets-tpl-16"
  subnet_ids = [aws_subnet.storage[0].id, aws_subnet.storage[1].id]
}

resource "aws_db_instance" "storage_db" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.storage_subnets.name
  engine                 = "postgres"
  identifier             = "storage-db-tpl-16"
  instance_class         = var.db_instance_class
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.storage_access.id]
}
