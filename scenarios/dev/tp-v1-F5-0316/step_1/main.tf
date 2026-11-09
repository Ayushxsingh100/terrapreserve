resource "aws_vpc" "main" {
    cidr_block = var.vpc_config.cidr_block
    tags = {
      Name = var.vpc_config.Name
    }
}

resource "aws_subnet" "main" {
    vpc_id = aws_vpc.main.id
    for_each = var.subnet_config  #kyunki subnet me list value hai isliye for_each use kiya
    cidr_block = each.value.cidr_block
    availability_zone = each.value.az 
}

#Internet Gateway if subnet is public (atleast 1 public)

locals {
    public_subnet = {
        #key={} if public is true in subnet_config
        for key , config in var.subnet_config : key => config if config.public   #agar public=false then key=0 
    }
    
    private_subnet = {
    #key={} if public is true in subnet_config
    for key, config in var.subnet_config : key => config if !config.public
  }                                                                         
}

resource "aws_internet_gateway" "igw" {
    vpc_id = aws_vpc.main.id
    count = length(local.public_subnet) > 0 ? 1 : 0   

    #public subnet agar 0 se jyada toh 1 baar hi IGW bnega else nahi banega
    #kitne baar mera public subnet chalega usko count krega 
}

#Route table
resource "aws_route_table" "Route" {
    vpc_id = aws_vpc.main.id
    count = length(local.public_subnet) > 0 ? 1:0
    route {
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.igw[0].id
    } 
}

#RouteTable Association
resource "aws_route_table_association" "main" {
    for_each = local.public_subnet
    subnet_id = aws_subnet.main[each.key].id
    route_table_id = aws_route_table.Route[0].id
}

#Route table association = Ye subnet kis raste (rules) se traffic bhejega/le aayega.


#Total Resources Added after Planning :
# 1 VPC,3 SUBNET,1 IGW,1 RT, 2 ROUTE TABLE ASSOCIATION = 8 resources