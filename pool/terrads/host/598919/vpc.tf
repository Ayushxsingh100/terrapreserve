resource "aws_vpc" "main" {
cidr_block = "10.0.0.0/16"
tags = {
Name = "multi-tier-vpc"
}
}
#Add Subnets
resource "aws_subnet" "public" {
vpc_id = aws_vpc.main.id
cidr_block = "10.0.1.0/24"
map_public_ip_on_launch = true
availability_zone = "us-east-1a"
tags = {
Name = "public-subnet"
}
}
resource "aws_subnet" "app" {
vpc_id = aws_vpc.main.id
cidr_block = "10.0.2.0/24"
availability_zone = "us-east-1b"
tags = {
Name = "app-subnet"
}
}
resource "aws_subnet" "db" {
vpc_id = aws_vpc.main.id
cidr_block = "10.0.3.0/24"
availability_zone = "us-east-1c"
tags = {
Name = "db-subnet"
}
}
#Add an Internet Gateway
resource "aws_internet_gateway" "main" {
vpc_id = aws_vpc.main.id
tags = {
Name = "multi-tier-igw"
}
}
#Add route Table
resource "aws_route_table" "public" {
vpc_id = aws_vpc.main.id
route {
cidr_block = "0.0.0.0/0"
gateway_id = aws_internet_gateway.main.id
}
}
resource "aws_route_table_association" "public" {
subnet_id = aws_subnet.public.id
route_table_id = aws_route_table.public.id
}