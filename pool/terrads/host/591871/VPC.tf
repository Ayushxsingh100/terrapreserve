/*
Here we are creating the actual resource/tangible infrustructure = aws_vpc ; which we named this
further more we are referencing our variable vpc-config which we have created in our variables template
*/

resource "aws_vpc" "vpc" {
  cidr_block = var.vpc_config.cidr_block

  /*
Here we are including some tags to help us identify our resources
we are referencing the name variable here in our variables template; named- vpc_name
*/
  tags = {
    Name = var.vpc_config.name
  }
}
#each value here is from the variable subnet_config > az =string
resource "aws_subnet" "subnet" {
  for_each          = var.subnet_config
  vpc_id            = aws_vpc.vpc.id
  availability_zone = each.value.az
  cidr_block        = each.value.cidr_block
  # coming from each module for the subnet_config, subnet 1 cidr range and az
  tags = {
    Name   = each.key
    Access = each.value.public ? "Public" : "Private"
  }
  lifecycle {
    # with this precondition we prevent terraform from going into apply mode with invalid values
    precondition {
      condition     = contains(data.aws_availability_zones.azs.names, each.value.az)
      error_message = <<-EOT
      THIS IS AN ERROR MESSAGE - The AZ "${each.value.az}" provided for the "${each.key}" is invalid

      The applied AWS region "${data.aws_availability_zones.azs.id}" supports the following AZs:
      [${join(",", data.aws_availability_zones.azs.names)}]
      EOT
    }
  }
}


data "aws_availability_zones" "azs" {
  state = "available"
}

locals {
  public_subnets = {
    for key, config in var.subnet_config : key => config if config.public
  }

  private_subnets = {
    for key, config in var.subnet_config : key => config if !config.public
  }
}

resource "aws_internet_gateway" "IG" {
  count  = length((local.public_subnets)) > 0 ? 1 : 0
  vpc_id = aws_vpc.vpc.id
}

resource "aws_route_table" "public_route_table" {
  count  = length(local.public_subnets) > 0 ? 1 : 0
  vpc_id = aws_vpc.vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.IG[0].id
  }
}


resource "aws_route_table_association" "public" {
  for_each       = local.public_subnets
  subnet_id      = aws_subnet.subnet[each.key].id
  route_table_id = aws_route_table.public_route_table[0].id


}