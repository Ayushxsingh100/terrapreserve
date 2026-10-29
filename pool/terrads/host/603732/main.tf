provider "aws" {
  region = var.aws_region
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_support = true
  enable_dns_hostnames = true
  tags = {
    Name = "main-vpc"
  }
}

resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone = "${var.aws_region}a"
  
  tags = {
    Name = "public-subnet"
  }
}

resource "aws_security_group" "default" {
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow SSH access"
  }
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP access"
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS access"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
  
  tags = {
    Name = "default-sg"
  }
}

# Instance configurations with minimal sizes for cost-efficiency.
# Adjust as needed for higher performance.

resource "aws_instance" "kafka" {
  ami           = var.ami_id
  instance_type = "t3.small"  # Minimum size; adjust for performance.
  subnet_id     = aws_subnet.public.id
  security_groups = [aws_security_group.default.name]
  key_name      = var.key_name

  tags = {
    Name = "kafka-server"
  }
}

resource "aws_instance" "logstash" {
  ami           = var.ami_id
  instance_type = "t3.small"  # Minimum size; adjust for performance.
  subnet_id     = aws_subnet.public.id
  security_groups = [aws_security_group.default.name]
  key_name      = var.key_name

  tags = {
    Name = "logstash-server"
  }
}

resource "aws_instance" "elasticsearch" {
  ami           = var.ami_id
  instance_type = "t3.medium"  # Minimum safe size for Elasticsearch; adjust as needed.
  subnet_id     = aws_subnet.public.id
  security_groups = [aws_security_group.default.name]
  key_name      = var.key_name

  tags = {
    Name = "elasticsearch-server"
  }
}

resource "aws_instance" "kibana" {
  ami           = var.ami_id
  instance_type = "t3.small"  # Minimum size; adjust for performance.
  subnet_id     = aws_subnet.public.id
  security_groups = [aws_security_group.default.name]
  key_name      = var.key_name

  tags = {
    Name = "kibana-server"
  }
}
