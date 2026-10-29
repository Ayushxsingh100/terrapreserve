provider "aws" {
  region = var.vpc_config.region
}

resource "aws_vpc" "test-vpc" {
  cidr_block = var.vpc_config.cidr_block
  tags = {
    Name = var.vpc_config.name
  }
}


resource "aws_subnet" "test-subnet" {
  for_each          = var.subnet_config
  vpc_id            = aws_vpc.test-vpc.id # the vpc id of the vpc created above 
  cidr_block        = each.value.cidr_block
  availability_zone = each.value.az
  tags = {
    Name = each.key
  }
}

# creating a local for counting the number of public subnets 

locals {
  public_subnet_count = {
    for key, config in var.subnet_config : key => config if config.is_public
  }
}

resource "aws_internet_gateway" "test-igw" {
  vpc_id = aws_vpc.test-vpc.id
  count  = length(local.public_subnet_count) > 0 ? 1 : 0 # we do not want to create 10 igw if there are 10 public subnets , that would be terrible 
  tags = {
    Name = "${var.vpc_config.name}-igw"
  }
}

resource "aws_route_table" "test-rtb" {
  vpc_id = aws_vpc.test-vpc.id
  count  = length(local.public_subnet_count) > 0 ? 1 : 0 # we do not want to create 10 rtb if there are 10 public subnets , that would be terrible
  tags = {
    Name = "${var.vpc_config.name}-rtb"
  }
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.test-igw[0].id # notice [0] because now we have a list of igw , with a length of 1 or 0
  }
}

resource "aws_route_table_association" "test-rtb-assoc" {
  for_each       = local.public_subnet_count           # local.public_subnet_count is a map of public subnets only
  subnet_id      = aws_subnet.test-subnet[each.key].id # each.key is like subnet1,subnet2 and we use it to get the id of the subnet from the aws_subnet resource , how? because we used for_each in the aws_subnet resource, so the resource is a map with keys like subnet1, subnet2 and values are the subnet objects like {id=...,cidr_block=...,az=...}, when we do map[key] we get the value of that key and here we want the id of that subnet so we do .id , we can do this because we used for_each in the aws_subnet resopurce
  route_table_id = aws_route_table.test-rtb[0].id      # notice [0] because now we have a list of rtb , with a length of 1 or 0
}
