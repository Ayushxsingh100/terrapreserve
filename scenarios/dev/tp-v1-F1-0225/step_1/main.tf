resource "aws_vpc" "name" {
	cidr_block = var.vpc_config.cidr_block
	tags = {
		Name = var.vpc_config.name
		}
}
resource "aws_subnet" "main" {
	vpc_id= aws_vpc.name.id
	for_each = var.subnet_config
	cidr_block = each.value.cidr_block
	availability_zone = each.value.az
	tags = {
	Name = each.key
	}
}
locals {
	public_subnet = {
		for k,v in var.subnet_config : k => v if v.public
	}
	private_subnet = {
                for k,v in var.subnet_config : k => v if v.public
        }

}
resource "aws_internet_gateway" "main" {
	vpc_id = aws_vpc.name.id
	count = length(local.public_subnet) > 0 ? 1 : 0
}
resource "aws_route_table" "name" {
	count = length(local.public_subnet) > 0 ? 1 : 0
	vpc_id = aws_vpc.name.id
	route {
	 	cidr_block = "0.0.0.0/0"
		gateway_id = aws_internet_gateway.main[0].id
	}
}
resource "aws_route_table_association" "main" {
	for_each = local.public_subnet
	subnet_id = aws_subnet.main[each.key].id
	route_table_id = aws_route_table.name[0].id
}	
