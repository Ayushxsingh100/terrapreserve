# ======VPC======
resource "aws_vpc" "demo-test-vpc" {
  cidr_block           = "10.123.0.0/16"
  instance_tenancy     = "default"
  enable_dns_hostnames = "true"

  tags = {
    Name = "demo-test-vpc"
  }
}

# ======Subnet======
resource "aws_subnet" "public-1a" {
  vpc_id                  = aws_vpc.demo-test-vpc.id
  cidr_block              = "10.123.1.0/28"
  availability_zone       = "ap-southeast-1a"
  map_public_ip_on_launch = "true"

  tags = {
    Name = "demo-test-vpc-public-1a"
  }
}
resource "aws_subnet" "public-1b" {
  vpc_id                  = aws_vpc.demo-test-vpc.id
  cidr_block              = "10.123.2.0/28"
  availability_zone       = "ap-southeast-1b"
  map_public_ip_on_launch = "true"

  tags = {
    Name = "demo-test-vpc-public-1b"
  }
}
resource "aws_subnet" "public-1c" {
  vpc_id                  = aws_vpc.demo-test-vpc.id
  cidr_block              = "10.123.3.0/28"
  availability_zone       = "ap-southeast-1c"
  map_public_ip_on_launch = "true"

  tags = {
    Name = "demo-test-vpc-public-1c"
  }
}

# ======IGW======
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.demo-test-vpc.id

  tags = {
    Name = "shwu-wiwynn-test-igw"
  }
}

# ======RouteTable======
resource "aws_route_table" "route-table" {
  vpc_id = aws_vpc.demo-test-vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "demo-test-vpc-route-table"
  }
}

resource "aws_route_table_association" "tf-vpc-01-rtb-at-pub" {
  subnet_id      = aws_subnet.public-1a.id
  route_table_id = aws_route_table.route-table.id
}

resource "aws_route_table_association" "tf-vpc-02-rtb-at-pub" {
  subnet_id      = aws_subnet.public-1b.id
  route_table_id = aws_route_table.route-table.id
}

resource "aws_route_table_association" "tf-vpc-03-rtb-at-pub" {
  subnet_id      = aws_subnet.public-1c.id
  route_table_id = aws_route_table.route-table.id
}

resource "aws_security_group" "demo-vpc-security-group" {
  name = "demo-vpc-security-group"
  vpc_id = aws_vpc.demo-test-vpc.id

  ingress {
    cidr_blocks = [
      "0.0.0.0/0"
    ]
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [
      "0.0.0.0/0"
    ]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [
      "0.0.0.0/0"
    ]
  }

  ingress {
    from_port   = 2000
    to_port     = 10000
    protocol    = "tcp"
    cidr_blocks = [
      "0.0.0.0/0"
    ]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [
      "0.0.0.0/0"
    ]
  }

  lifecycle {
    create_before_destroy = true
  }
}

output "aws_vpc_id" {
  value = aws_vpc.demo-test-vpc.id
}

output "aws_vpc_details" {
  value = [
	  aws_subnet.public-1a,
	  aws_subnet.public-1b,
	  aws_subnet.public-1c
  ]
}

