resource "aws_vpc" "main" {
  cidr_block           = var.cidr_block
  instance_tenancy     = "default"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = var.tags
}


resource "aws_subnet" "public1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet1
  map_public_ip_on_launch = true
  tags                    = var.tags
}

resource "aws_subnet" "public2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet2
  map_public_ip_on_launch = true
  tags                    = var.tags
}
resource "aws_subnet" "public3" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet3
  map_public_ip_on_launch = true
  tags                    = var.tags
}
resource "aws_subnet" "private1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet1
  map_public_ip_on_launch = false
  tags                    = var.tags
}
resource "aws_subnet" "private2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet2
  map_public_ip_on_launch = false
  tags                    = var.tags
}
resource "aws_subnet" "private3" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet3
  map_public_ip_on_launch = false
  tags                    = var.tags
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
  tags   = var.tags
}


/* resource "aws_eip" "nat" {
  vpc = true
}
resource "aws_nat_gateway" "example" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public1.id
  depends_on    = [aws_internet_gateway.gw]
  tags          = var.tags
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_nat_gateway.example.id
  }
  tags = var.tags
}
resource "aws_route_table_association" "private1" {
  subnet_id      = aws_subnet.private1.id
  route_table_id = aws_route_table.private.id
}
resource "aws_route_table_association" "private2" {
  subnet_id      = aws_subnet.private2.id
  route_table_id = aws_route_table.private.id
}
resource "aws_route_table_association" "private3" {
  subnet_id      = aws_subnet.private3.id
  route_table_id = aws_route_table.private.id
} */






/* # resource "aws_instance" "web" {
    ami = "ami-07be51e3c6d5f61d2"
    instance_type = "t3.micro"
    associate_public_ip_address = true
    availability_zone = "eu-west-1a"
    key_name = aws_key_pair.first.key_name
}

resource "aws_key_pair" "first" {
    key_name = "first_key"
    public_key = file("~/.ssh/id_rsa.pub")
}

resource "aws_security_group" "class2" {
  name        = "class2"
  description = "Allow TLS inbound traffic"

  ingress {
    description = "TLS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "TLS from VPC"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }


  ingress {
    description = "TLS from VPC"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}
 */