resource "aws_vpc" "vpc" {
  cidr_block = var.vpc_cidr
  enable_dns_hostnames = true

  tags = {
    environment = var.environment
  }
}

resource "aws_internet_gateway" "elk_igw" {
  vpc_id = aws_vpc.vpc.id

  tags = {
    environment = var.environment
  }
}

resource "aws_route_table" "elk_rt" {
  vpc_id = aws_vpc.vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.elk_igw.id
  }

  tags = {
    environment = var.environment
  }
}

resource "aws_route_table_association" "elk_rt_assoc" {
  subnet_id      = aws_subnet.elk.id
  route_table_id = aws_route_table.elk_rt.id
}

resource "aws_subnet" "elk" {
  vpc_id                  = aws_vpc.vpc.id
  cidr_block              = var.subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = var.availability_zone

  tags = {
    environment = var.environment
  }
}

resource "aws_security_group" "elk_sg" {
  name        = "elk-allow"
  description = "Allow incoming ELK traffic and Connections"
  vpc_id      = aws_vpc.vpc.id

  ingress {
    description = "Allow HTTP internet traffic ingress"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow HTTPS internet traffic ingress"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow SSH traffic ingress"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Kibana"
    from_port   = 5601
    to_port     = 5601
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Transport"
    from_port   = 9300
    to_port     = 9300
    protocol    = "tcp"
    cidr_blocks = [var.subnet_cidr]
  }

  ingress {
    description = "Elasticsearch"
    from_port   = 9200
    to_port     = 9200
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    environment = var.environment
  }
}

