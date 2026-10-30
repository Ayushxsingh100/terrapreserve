# 사용하고자 하는 AWS 리전: 서울
provider "aws" {
  region = "ap-northeast-2"
}

# VPC 설정
resource "aws_vpc" "ai_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "ai_vpc"
  }
}

# Subnet 설정 (AI 서버용 Public Subnet)
resource "aws_subnet" "ai_subnet_public" {
  vpc_id                  = aws_vpc.ai_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "ap-northeast-2a"

  tags = {
    Name = "ai_subnet_public"
  }
}

# Internet Gateway 설정
resource "aws_internet_gateway" "ai_igw" {
  vpc_id = aws_vpc.ai_vpc.id

  tags = {
    Name = "ai_igw"
  }
}

# Route Table 설정
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.ai_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.ai_igw.id
  }

  tags = {
    Name = "public_rt"
  }
}

# Subnet과 Route Table 연결
resource "aws_route_table_association" "public_rt_assoc_ai" {
  subnet_id      = aws_subnet.ai_subnet_public.id
  route_table_id = aws_route_table.public_rt.id
}

# Security Group 설정
resource "aws_security_group" "ai_sg" {
  vpc_id = aws_vpc.ai_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # 8000 포트 추가
  ingress {
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
    Name = "ai_sg"
  }
}

# AI Server (Public Subnet)
resource "aws_instance" "ai_server" {
  ami                         = "ami-062cf18d655c0b1e8" # 적절한 AMI 사용
  instance_type               = "t3.medium"
  subnet_id                   = aws_subnet.ai_subnet_public.id
  associate_public_ip_address = true
  key_name                    = "kakao-tech-bootcamp" # SSH 키 이름
  security_groups             = [aws_security_group.ai_sg.id]

  tags = {
    Name = "AI-Server"
  }
}
