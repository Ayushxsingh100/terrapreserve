resource "aws_vpc" "main" {
  cidr_block = var.cidr
  
    tags = merge(
    {
      "Name" = format("%s", var.name)
    },
    # var.tags,
    # var.vpc_tags,
  )
}

#####################
#public subnet part
#####################

#cria as public subnets

resource "aws_subnet" "public_subnet" {
  count = length(var.public_subnets)
  #count = var.azs_count
  vpc_id     = aws_vpc.main.id
  cidr_block = element(var.public_subnets, count.index)
  #availability_zone = element(var.use-az_id, count.index)
  availability_zone_id = element(var.use_az_id, count.index) 
  
 tags = merge( {"Name" = format("%s_public_subnet_%s", var.name, element(var.use_az_id, count.index),)},) 
}

#cria as public route tables

resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.main.id
  count = length(var.public_subnets)
  # route {
  #   cidr_block = "10.0.1.0/24"
  #   gateway_id = aws_internet_gateway.example.id
  # }

  tags = merge( {"Name" = format("%s_public_route_table_%s", var.name, element(var.use_az_id, count.index),)},) 
}

#associa as public route tables nas devidas subnets

resource "aws_route_table_association" "public_route_table_association" {
  count = length(var.public_subnets)

  subnet_id       = element(aws_subnet.public_subnet.*.id, count.index)
  route_table_id  = element(aws_route_table.public_route_table.*.id, count.index,
  )
}


#####################
#private subnet part
#####################

#cria as private subnets

resource "aws_subnet" "private_subnet" {
  count = length(var.private_subnets)
  #count = var.azs_count
  vpc_id     = aws_vpc.main.id
  cidr_block = element(var.private_subnets, count.index)
  #availability_zone = element(var.use-az_id, count.index)
  availability_zone_id = element(var.use_az_id, count.index) 
  
 tags = merge( {"Name" = format("%s_private_subnet_%s", var.name, element(var.use_az_id, count.index),)},) 
}

#cria as private route tables

resource "aws_route_table" "private_route_table" {
  vpc_id = aws_vpc.main.id
  count = length(var.private_subnets)
  # route {
  #   cidr_block = "10.0.1.0/24"
  #   gateway_id = aws_internet_gateway.example.id
  # }

  tags = merge( {"Name" = format("%s_private_route_table_%s", var.name, element(var.use_az_id, count.index),)},) 
}

#associa as private route tables nas devidas subnets

resource "aws_route_table_association" "private_route_table_association" {
  count = length(var.private_subnets)

  subnet_id       = element(aws_subnet.private_subnet.*.id, count.index)
  route_table_id  = element(aws_route_table.private_route_table.*.id, count.index,
  )
}


#####################
#endpoint subnet part
#####################

#cria as endpoint subnets

resource "aws_subnet" "endpoint_subnet" {
  count = length(var.endpoint_subnets)
  #count = var.azs_count
  vpc_id     = aws_vpc.main.id
  cidr_block = element(var.endpoint_subnets, count.index)
  #availability_zone = element(var.use-az_id, count.index)
  availability_zone_id = element(var.use_az_id, count.index) 
  
 tags = merge( {"Name" = format("%s_endpoint_subnet_%s", var.name, element(var.use_az_id, count.index),)},) 
}

#cria as endpoint route tables

resource "aws_route_table" "endpoint_route_table" {
  vpc_id = aws_vpc.main.id
  count = length(var.endpoint_subnets)
  # route {
  #   cidr_block = "10.0.1.0/24"
  #   gateway_id = aws_internet_gateway.example.id
  # }

  tags = merge( {"Name" = format("%s_endpoint_route_table_%s", var.name, element(var.use_az_id, count.index),)},) 
}

#associa as endpoint route tables nas devidas subnets

resource "aws_route_table_association" "endpoint_route_table_association" {
  count = length(var.endpoint_subnets)

  subnet_id       = element(aws_subnet.endpoint_subnet.*.id, count.index)
  route_table_id  = element(aws_route_table.endpoint_route_table.*.id, count.index,
  )
}