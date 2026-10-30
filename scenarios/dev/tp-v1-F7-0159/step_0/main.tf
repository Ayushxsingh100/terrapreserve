resource "aws_vpc" "network" {
  cidr_block           = "10.174.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "gateway" {
  vpc_id = aws_vpc.network.id
}

resource "aws_subnet" "web_tier" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.174.1.0/24"
  vpc_id            = aws_vpc.network.id
}

resource "aws_subnet" "data_tier" {
  count = 3

  availability_zone = ["us-east-1a", "us-east-1b", "us-east-1c"][count.index]
  cidr_block        = ["10.174.10.0/24", "10.174.11.0/24", "10.174.12.0/24"][count.index]
  vpc_id            = aws_vpc.network.id
}

resource "aws_route_table" "public_route" {
  vpc_id = aws_vpc.network.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gateway.id
  }
}

resource "aws_route_table_association" "assoc_app" {
  route_table_id = aws_route_table.public_route.id
  subnet_id      = aws_subnet.web_tier.id
}

resource "aws_security_group_rule" "data_secgroup_from_app_5432" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.data_secgroup.id
  source_security_group_id = aws_security_group.web_secgroup.id
  to_port                  = 5432
  type                     = "ingress"
}

resource "aws_security_group_rule" "data_secgroup_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.data_secgroup.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group" "web_secgroup" {
  description = "Application security group for tpl-03"
  name        = "web_secgroup-tpl-03"
  vpc_id      = aws_vpc.network.id

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }
}

resource "aws_security_group" "data_secgroup" {
  description = "Database security group for tpl-03"
  name        = "data_secgroup-tpl-03"
  vpc_id      = aws_vpc.network.id
}

resource "aws_instance" "web_instance" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.nano"
  subnet_id              = aws_subnet.web_tier.id
  vpc_security_group_ids = [aws_security_group.web_secgroup.id]
}

resource "aws_db_subnet_group" "data_subnets" {
  name       = "data_subnets-tpl-03"
  subnet_ids = [aws_subnet.data_tier[0].id, aws_subnet.data_tier[1].id, aws_subnet.data_tier[2].id]
}

resource "aws_db_instance" "data_instance" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.data_subnets.name
  engine                 = "postgres"
  identifier             = "data-instance-tpl-03"
  instance_class         = "db.t3.micro"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.data_secgroup.id]
}
