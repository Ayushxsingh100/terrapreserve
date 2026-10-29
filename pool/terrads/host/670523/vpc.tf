# locals block introduced as part of excerise 41
locals {
  public_subnets = {
    for key, config in var.subnet_config : key => config if config.public
  }

  private_subnets = {
    for key, config in var.subnet_config : key => config if !config.public
  }
}



# below introduced in first part excerise 38
# resource "aws_vpc" "this" {
#   cidr_block = var.vpc_cidr

#   tags = {
#     Name = var.vpc_name
#   }
# }

# below data block introduced in excerise 40

data "aws_availability_zones" "available" {
  state = "available"
}

# below resource block introduced in second part of excerise 38
resource "aws_vpc" "this" {
  cidr_block = var.vpc_config.cidr_block

  tags = {
    Name = var.vpc_config.name
  }
}


# below resource block introduced in excerise 39
resource "aws_subnet" "this" {
  for_each          = var.subnet_config
  vpc_id            = aws_vpc.this.id
  availability_zone = each.value.az
  cidr_block        = each.value.cidr_block

  tags = {
    Name   = each.key                                 # ie. subnet_X
    Access = each.value.public ? "Public" : "Private" # This line added as final step in excerise 43
  }

  # below lifecycle block introduced as part of excerise 40
  lifecycle {
    precondition {
      condition = contains(data.aws_availability_zones.available.names, each.value.az)
      #   error_message = "Invalid AZ" # simple error_message


      # more elegant error message for each of the parameters involved.     
      #   error_message = <<-EOT
      #   Subnet key: ${each.key}
      #   AWS Region: ${data.aws_availability_zones.available.id}
      #   Invalid AZ: ${each.value.az}
      #   List of supported AZs: ${data.aws_availability_zones.available.names}
      #   EOT

      # Final elaborate/elegant error message below.      
      error_message = <<-EOT
      The AZ "${each.value.az}" provided for the subnet "${each.key}" is invalid.

      The applied AWS region "${data.aws_availability_zones.available.id}" supports the following AZs:
      [${join(", ", data.aws_availability_zones.available.names)}]
      EOT
    }
  }

}

# below resource of aws_internet_gateway introduced in excerise 41
resource "aws_internet_gateway" "this" {
  count  = length(local.public_subnets) > 0 ? 1 : 0
  vpc_id = aws_vpc.this.id
}


# below resource of aws_route_table introduced in excerise 41
resource "aws_route_table" "public_rtb" {
  count  = length(local.public_subnets) > 0 ? 1 : 0
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this[0].id
  }
}


# below resource of aws_route_table_association introduced in excerise 41
resource "aws_route_table_association" "public" {
  for_each = local.public_subnets

  subnet_id      = aws_subnet.this[each.key].id
  route_table_id = aws_route_table.public_rtb[0].id
}