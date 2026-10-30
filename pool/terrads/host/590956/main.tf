resource "aws_vpc" "spacelift_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true

  tags = {
    Name = "spacelift"
  }

}

resource "aws_subnet" "spacelift_public_subnet" {
  vpc_id                  = aws_vpc.spacelift_vpc.id
  cidr_block              = "10.0.0.0/16"
  map_public_ip_on_launch = true
  availability_zone       = "us-east-1a"

  tags = {
    Name = "spacelift-public-subnet"
  }
}

resource "aws_security_group" "allow_access" {
  name        = "spacelift-sg"
  description = "Allow SSH, HTTP and HTTPS traffic"
  vpc_id      = aws_vpc.spacelift_vpc.id
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 8000
    to_port     = 8000
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
    Name = "spacelift-sg"
  }
}
