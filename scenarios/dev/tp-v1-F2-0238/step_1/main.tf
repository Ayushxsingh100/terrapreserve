resource "aws_vpc" "main" {
    cidr_block = var.vpc_config.cidr_block
    tags={
        Name=var.vpc_config.name
    }
}

resource "aws_subnet" "subnet"{
    vpc_id = aws_vpc.main.id
    for_each = var.subnet_config
    cidr_block = each.value.cidr_block
    availability_zone = each.value.az
    tags={
        Name=each.key
    }
}

locals{
    public_subnet={
        # checks if there is public subnet
        for key,config in var.subnet_config:key=>config if config.public
    }
        private_subnet={
        # checks if there is public subnet
        for key,config in var.subnet_config:key=>config if !config.public
    }
}

resource "aws_internet_gateway" "ig" {
  vpc_id=aws_vpc.main.id
#   if there is public subnet , create a internet gateway
  count=length(local.public_subnet) > 0 ? 1 : 0 
}

resource "aws_route_table" "name" {
  vpc_id=aws_vpc.main.id
  count=length(local.public_subnet) > 0 ? 1 : 0 

    route{
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.ig[0].id
    }
}

resource "aws_route_table_association" "main" {
    for_each = local.public_subnet
    subnet_id = aws_subnet.subnet[each.key].id
    route_table_id = aws_route_table.name[0].id
  
}



# 
# +---------------------------+
# |        Start               |
# +---------------------------+
#             |
#             v
# +---------------------------+
# | Input VPC CIDR Block       |
# | (User provides CIDR block) |
# +---------------------------+
#             |
#             v
# +---------------------------+
# |       Create VPC           |
# | (Using the CIDR block)     |
# +---------------------------+
#             |
#             v
# +-----------------------------------+
# |  For Each Subnet Configuration    |
# |  (Loop over user-provided subnets)|
# +-----------------------------------+
#             |
#             v
# +-----------------------------------+
# | Input Subnet CIDR Block,          |
# | Availability Zone, and            |
# | Public/Private Flag               |
# +-----------------------------------+
#             |
#             v
# +---------------------------+
# |       Create Subnet        |
# | (With provided CIDR block, |
# | Availability Zone, and Flag)|
# +---------------------------+
#             |
#             v
# +---------------------------+
# | Is Subnet Public?         |
# | (Decision Point)          |
# +---------------------------+
#        |         |
#        |         v
#        |     +---------------------------+
#        |     | No: Add to Private Subnets |
#        |     +---------------------------+
#        |
#        v
# +-----------------------------------+
# | Yes: Add to Public Subnets List   |
# +-----------------------------------+
#             |
#             v
# +---------------------------+
# | Check if Any Public Subnets|
# | Exist (Decision Point)     |
# +---------------------------+
#        |         |
#        |         v
#        |     +---------------------------+
#        |     | No: Skip IGW and           |
#        |     | Route Table Creation       |
#        |     +---------------------------+
#        |
#        v
# +-------------------------------+
# | Yes: Create Internet Gateway  |
# | (IGW for VPC)                 |
# +-------------------------------+
#             |
#             v
# +-------------------------------+
# | Create Route Table            |
# | (For public subnets)          |
# +-------------------------------+
#             |
#             v
# +-------------------------------+
# | Associate Route Table with    |
# | Public Subnets                |
# +-------------------------------+
#             |
#             v
# +---------------------------+
# |          End              |
# +---------------------------+
