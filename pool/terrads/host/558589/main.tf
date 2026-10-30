
# AWS Availability Zones
data "aws_availability_zones" "available_zones" {}
locals {
  offset = length(data.aws_availability_zones.available_zones.names)
}
resource "aws_subnet" "subnet" {
  count             = length(data.aws_availability_zones.available_zones.names)
  cidr_block        = cidrsubnet(var.cidr, var.subnet_bits, local.offset * var.offset + count.index)
  vpc_id            = var.vpc_id
  availability_zone = data.aws_availability_zones.available_zones.names[count.index]
  tags = {
    Name       = "${var.cluster_prefix}-${lower(var.subnet_type)}-subnet-${count.index + 1}"
  }
}