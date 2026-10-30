resource "aws_vpc" "main" {
  cidr_block           = var.cidr_block
  instance_tenancy     = "default"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = var.tags
}
resource "aws_subnet" "public1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet1
  tags                    = var.tags
  map_public_ip_on_launch = true
  availability_zone = "us-east-1a"
}


resource "aws_subnet" "public2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet2
  tags                    = var.tags
  map_public_ip_on_launch = true
  availability_zone = "us-east-1b"
}
resource "aws_subnet" "public3" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet3
  tags                    = var.tags
  map_public_ip_on_launch = true
  availability_zone = "us-east-1c"
}
resource "aws_subnet" "private1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet1
  tags                    = var.tags
  map_public_ip_on_launch = false
  availability_zone = "us-east-1d"
}
resource "aws_subnet" "private2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet2
  tags                    = var.tags
  map_public_ip_on_launch = false
  availability_zone = "us-east-1e"

}
resource "aws_subnet" "private3" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.private_subnet3
  tags                    = var.tags
  map_public_ip_on_launch = false
  availability_zone = "us-east-1f"
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
  tags   = var.tags
}


resource "aws_route_table" "startup" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
  tags = var.tags

}
resource "aws_route_table_association" "public1" {
  subnet_id      = aws_subnet.public1.id
  route_table_id = aws_route_table.startup.id
}
resource "aws_route_table_association" "public2" {
  subnet_id      = aws_subnet.public2.id
  route_table_id = aws_route_table.startup.id
}
resource "aws_route_table_association" "public3" {
  subnet_id      = aws_subnet.public3.id
  route_table_id = aws_route_table.startup.id
}



# resource "aws_eip" "ngw" {
#   domain = "vpc"
# }
# resource "aws_nat_gateway" "example" {
#   allocation_id = aws_eip.ngw.id
#   subnet_id     = aws_subnet.public1.id


#   # To ensure proper ordering, it is recommended to add an explicit dependency
#   # on the Internet Gateway for the VPC.
#   depends_on = [aws_internet_gateway.gw]
#   tags       = var.tags
# }
# resource "aws_route_table" "private" {
#   vpc_id = aws_vpc.main.id

#   route {
#     cidr_block = "0.0.0.0/0"
#     gateway_id = aws_nat_gateway.example.id
#   }
#   tags = var.tags

# }
# resource "aws_route_table_association" "private1" {
#   subnet_id      = aws_subnet.private1.id
#   route_table_id = aws_route_table.private.id
# }
# resource "aws_route_table_association" "private2" {
#   subnet_id      = aws_subnet.private2.id
#   route_table_id = aws_route_table.private.id
# }
# resource "aws_route_table_association" "private3" {
#   subnet_id      = aws_subnet.private3.id
#   route_table_id = aws_route_table.private.id
# }