
# AWS Availability Zones
locals {
  offset = length(var.tp_ds_aws_availability_zones_available_zones.names)
}
resource "aws_subnet" "subnet" {
  count             = length(var.tp_ds_aws_availability_zones_available_zones.names)
  cidr_block        = cidrsubnet(var.cidr, var.subnet_bits, local.offset * var.offset + count.index)
  vpc_id            = var.vpc_id
  availability_zone = var.tp_ds_aws_availability_zones_available_zones.names[count.index]
  tags = {
    Name       = "${var.cluster_prefix}-${lower(var.subnet_type)}-subnet-${count.index + 1}"
  }
}