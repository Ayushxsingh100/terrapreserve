# VPC
resource "aws_vpc" "taskplanner_vpc" {
  cidr_block = var.vpc_cidr_block

  enable_dns_hostnames = true

  tags = {
    Name = "TaskPlannerVPC"
  }
}

# PUBLIC SUBNETS
resource "aws_subnet" "taskplanner_public_subnet" {
  count = length(var.public_subnet_cidr_blocks)

  vpc_id            = aws_vpc.taskplanner_vpc.id
  cidr_block        = var.public_subnet_cidr_blocks[count.index]
  availability_zone = var.availability_zones[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name = "TaskPlannerPublicSubnet${count.index + 1}"
  }
}

# PRIVATE SUBNETS
resource "aws_subnet" "taskplanner_private_subnet" {
  count = length(var.private_subnet_cidr_blocks)

  vpc_id            = aws_vpc.taskplanner_vpc.id
  cidr_block        = var.private_subnet_cidr_blocks[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "TaskPlannerPrivateSubnet${count.index + 1}"
  }
}

# INTERNET GATEWAY
resource "aws_internet_gateway" "taskplanner_igw" {
  vpc_id = aws_vpc.taskplanner_vpc.id

  tags = {
    Name = "TaskPlannerIGW"
  }
}

# PUBLIC ROUTE TABLE
resource "aws_route_table" "taskplanner_public_route_table" {
  vpc_id = aws_vpc.taskplanner_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.taskplanner_igw.id
  }

  tags = {
    Name = "TaskPlannerPublicRouteTable"
  }
}

resource "aws_route_table_association" "public_subnet_associations" {
  count = length(var.public_subnet_cidr_blocks)

  subnet_id      = aws_subnet.taskplanner_public_subnet.*.id[count.index]
  route_table_id = aws_route_table.taskplanner_public_route_table.id
}

# PRIVATE ROUTE TABLE
resource "aws_route_table" "taskplanner_private_route_table" {
  vpc_id = aws_vpc.taskplanner_vpc.id

  tags = {
    Name = "TaskPlannerPrivateRouteTable"
  }
}

resource "aws_route_table_association" "public_private_associations" {
  count = length(var.private_subnet_cidr_blocks)

  subnet_id      = aws_subnet.taskplanner_private_subnet.*.id[count.index]
  route_table_id = aws_route_table.taskplanner_private_route_table.id
}

# SECURITY GROUP
resource "aws_security_group" "taskplanner_security_group" {
  name_prefix = "taskplanner-sg-"

  vpc_id = aws_vpc.taskplanner_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

   ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}