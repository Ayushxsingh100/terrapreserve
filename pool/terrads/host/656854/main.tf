provider "aws" {
  region = "us-east-1"
}

# VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "VPC-Exercici2"
  }
}

# Subnets
resource "aws_subnet" "subnet_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.32.0/25"
  availability_zone = "us-east-1a"
  tags = {
    Name = "SubnetA"
  }
}

resource "aws_subnet" "subnet_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.30.0/23"
  availability_zone = "us-east-1a"
  tags = {
    Name = "SubnetB"
  }
}

resource "aws_subnet" "subnet_c" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.33.0/28"
  availability_zone = "us-east-1a"
  tags = {
    Name = "SubnetC"
  }
}

# Security Group
resource "aws_security_group" "ec2_sg" {
  name        = "ec2_sg"
  description = "Allow SSH"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
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
    Name = "EC2-SG"
  }
}

# Instancias EC2 por subnet
resource "aws_instance" "ec2_subnet_a_1" {
  ami                    = "ami-052064a798f08f0d3"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet_a.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  tags = {
    Name = "EC2-SubnetA-1"
  }
}

resource "aws_instance" "ec2_subnet_a_2" {
  ami                    = "ami-052064a798f08f0d3"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet_a.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  tags = {
    Name = "EC2-SubnetA-2"
  }
}

resource "aws_instance" "ec2_subnet_b_1" {
  ami                    = "ami-052064a798f08f0d3"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet_b.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  tags = {
    Name = "EC2-SubnetB-1"
  }
}

resource "aws_instance" "ec2_subnet_b_2" {
  ami                    = "ami-052064a798f08f0d3"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet_b.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  tags = {
    Name = "EC2-SubnetB-2"
  }
}

resource "aws_instance" "ec2_subnet_c_1" {
  ami                    = "ami-052064a798f08f0d3"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet_c.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  tags = {
    Name = "EC2-SubnetC-1"
  }
}

resource "aws_instance" "ec2_subnet_c_2" {
  ami                    = "ami-052064a798f08f0d3"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet_c.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  tags = {
    Name = "EC2-SubnetC-2"
  }
}
