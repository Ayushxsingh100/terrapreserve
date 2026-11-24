locals {
  total_subnets  = ((var.enable_public_subnets ? 1 : 0) + (var.enable_nat_subnets ? 1 : 0) + (var.enable_private_subnets ? 1 : 0)) * var.number_of_availability_zones
  subnet_newbits = ceil(log(local.total_subnets, 2))
}
