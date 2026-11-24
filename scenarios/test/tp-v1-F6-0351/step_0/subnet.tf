


resource "aws_subnet" "prod_subnet_1" {
  vpc_id            = var.tp_ds_aws_vpc_prod_vpc.id
  availability_zone = var.tp_ds_aws_availability_zones_working.names[0]
  cidr_block        = "172.31.0.0/16"
  tags = {
    Name    = "Subnet-1 in ${var.tp_ds_aws_availability_zones_working.names[0]}"
    Account = "Subnet in ${var.tp_ds_aws_caller_identity_current.account_id}"
    Region  = var.tp_ds_aws_region_current.description
  }
}

resource "aws_subnet" "prod_subnet_2" {
  vpc_id            = var.tp_ds_aws_vpc_prod_vpc.id
  availability_zone = var.tp_ds_aws_availability_zones_working.names[1]
  cidr_block        = "172.32.0.0/16"
  tags = {
    Name    = "Subnet-2 in ${var.tp_ds_aws_availability_zones_working.names[1]}"
    Account = "Subnet in ${var.tp_ds_aws_caller_identity_current.account_id}"
    Region  = var.tp_ds_aws_region_current.description
  }
}

output "availability_zones" {
  value = var.tp_ds_aws_availability_zones_working.names
}

output "data_aws_caller_identity" {
  value = var.tp_ds_aws_caller_identity_current.account_id
}

output "data_aws_region_name" {
  value = var.tp_ds_aws_region_current.name
}

output "data_aws_region_description" {
  value = var.tp_ds_aws_region_current.description
}

output "aws_vpcs" {
  value = var.tp_ds_aws_vpcs_my_vpcs.ids
}

output "prod_vpc_id" {
  value = var.tp_ds_aws_vpc_prod_vpc.id
}

output "prod_vpc_cidr" {
  value = var.tp_ds_aws_vpc_prod_vpc.cidr_block
}