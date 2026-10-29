provider "aws" {
  region = "us-east-1"
}

# VPC
resource "aws_vpc" "vpc_03" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "vpc_03"
  }
}

# Subnets
resource "aws_subnet" "subnet_A" {
  vpc_id                  = aws_vpc.vpc_03.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "subnet_A"
  }
}

resource "aws_subnet" "subnet_B" {
  vpc_id                  = aws_vpc.vpc_03.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "us-east-1b"
  map_public_ip_on_launch = true

  tags = {
    Name = "subnet_B"
  }
}

# Internet gateway
resource "aws_internet_gateway" "gateway" {
  vpc_id = aws_vpc.vpc_03.id
}

# Tabla de rutas
resource "aws_route_table" "tabla_rutas" {
  vpc_id = aws_vpc.vpc_03.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gateway.id
  }
}

# Asociarlas a las subnets
resource "aws_route_table_association" "A" {
  subnet_id      = aws_subnet.subnet_A.id
  route_table_id = aws_route_table.tabla_rutas.id
}

resource "aws_route_table_association" "B" {
  subnet_id      = aws_subnet.subnet_B.id
  route_table_id = aws_route_table.tabla_rutas.id
}

# Grup de seguretat
resource "aws_security_group" "grupo_seguridad" {
  name        = "grupo_seguridad"
  description = "Permitir acceso SSH desde cualquier parte, transito ICMP solo dentro de la VPC y permitir todo el trafico salientel"
  vpc_id      = aws_vpc.vpc_03.id


  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "ICMP des de VPC"
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = [aws_vpc.vpc_03.cidr_block]
  }
}

# Regla de salida
resource "aws_security_group_rule" "egress_todo" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.grupo_seguridad.id
}

# Instancias
resource "aws_instance" "subnet_A_instances" {
  ami                    = "ami-052064a798f08f0d3"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet_A.id
  vpc_security_group_ids = [aws_security_group.grupo_seguridad.id]
  key_name               = "vockey"

  tags = {
    Name = "ec2-a"
  }
}

resource "aws_instance" "subnet_B_instances" {
  ami                    = "ami-052064a798f08f0d3"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet_B.id
  vpc_security_group_ids = [aws_security_group.grupo_seguridad.id]
  key_name               = "vockey"

  tags = {
    Name = "ec2-b"
  }
}
