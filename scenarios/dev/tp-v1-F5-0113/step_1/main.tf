moved {
  from = aws_security_group_rule.storage_access_from_app_5432
  to   = aws_security_group_rule.storage_access_from_app_5432_v2
}

resource "aws_vpc" "platform" {
  cidr_block           = "10.193.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "edge" {
  vpc_id = aws_vpc.platform.id
}

resource "aws_subnet" "service" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.193.1.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_subnet" "storage_1" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.193.10.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_subnet" "storage_2" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.193.11.0/24"
  vpc_id            = aws_vpc.platform.id
}

resource "aws_subnet" "storage_3" {
  availability_zone = "us-east-1c"
  cidr_block        = "10.193.12.0/24"
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

resource "aws_security_group_rule" "storage_access_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.storage_access.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group_rule" "service_access_egress_db" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.service_access.id
  source_security_group_id = aws_security_group.storage_access.id
  to_port                  = 5432
  type                     = "egress"
}

resource "aws_security_group" "service_access" {
  description = "Application security group for tpl-31"
  name        = "service_access-tpl-31"
  vpc_id      = aws_vpc.platform.id
}

resource "aws_security_group" "storage_access" {
  description = "Database security group for tpl-31"
  name        = "storage_access-tpl-31"
  vpc_id      = aws_vpc.platform.id
}

resource "aws_security_group" "service_access_ops" {
  description = "Operations security group for tpl-31, attached to nothing"
  name        = "service_access_ops-tpl-31"
  vpc_id      = aws_vpc.platform.id

  ingress {
    cidr_blocks = ["10.193.0.0/16"]
    from_port   = 443
    protocol    = "tcp"
    to_port     = 443
  }
}

resource "aws_instance" "service_node" {
  ami                    = local.app_ami
  instance_type          = local.app_instance_type
  subnet_id              = aws_subnet.service.id
  vpc_security_group_ids = [aws_security_group.service_access.id]
}

resource "aws_db_subnet_group" "storage_subnets" {
  name       = "storage_subnets-tpl-31"
  subnet_ids = [aws_subnet.storage_1.id, aws_subnet.storage_2.id, aws_subnet.storage_3.id]
}

resource "aws_db_instance" "storage_db" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.storage_subnets.name
  engine                 = "postgres"
  identifier             = "storage-db-tpl-31"
  instance_class         = local.db_instance_class
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.storage_access.id]
}

resource "aws_security_group_rule" "storage_access_from_app_5432_v2" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.storage_access.id
  source_security_group_id = aws_security_group.service_access.id
  to_port                  = 5432
  type                     = "ingress"
}
